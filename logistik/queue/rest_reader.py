import sys
import logging
from uuid import uuid4 as uuid
import traceback
from collections import defaultdict
from typing import Union, List

from flask import request
from flask_restful import Resource

from activitystreams import parse as parse_as
from activitystreams import Activity

from logistik.utils.exceptions import ParseException
from logistik.queue import IRestReader
from logistik.config import ConfigKeys, ErrorCodes
from logistik.environ import GNEnvironment
from logistik.handlers.base import IHandler
from logistik.db.repr.handler import HandlerConf

ONE_MINUTE = 60_000


class RestConsumer(Resource):
    def __init__(self, **kwargs):
        super().__init__()
        self.conf: HandlerConf = kwargs.get('conf')
        self.env = kwargs.get('env')
        self.handler: IHandler = kwargs.get('handler')
        self.enabled = True
        self.reader = kwargs.get('reader')
        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.logger = logging.getLogger(__name__)

        self.reader.register_consumer(self)
        self.create_loggers()

    def stop(self):
        self.enabled = False

    def start(self):
        self.enabled = True

    def post(self) -> (Union[dict, str], int):
        if not self.enabled:
            return 'endpoint disabled', 400

        try:
            json_data = request.get_json()
        except Exception as e:
            error_msg = 'failed to parse json data: {}'.format(str(e))
            self.logger.error(error_msg)
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            return error_msg, 400

        try:
            return self.handle_message(json_data)
        except Exception as e:
            error_msg = 'failed to handle message: {}'.format(str(e))
            self.logger.error(error_msg)
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.fail_msg(json_data)
            return error_msg, 500

    def handle_message(self, message) -> (Union[dict, str], int):
        self.logger.debug(message)

        try:
            data, activity = self.try_to_parse(message)
            self.log_pre_processed_request(self.conf.reader_endpoint, data)
        except ParseException as e:
            error_msg = 'could not enrich/parse data because "{}", original data was: {}'.format(str(e), str(message))
            self.logger.error(error_msg)
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.handler_stats.error(self.conf, None)
            self.fail_msg(message)
            return error_msg, 400
        except Exception as e:
            error_msg = 'got uncaught exception: {}'.format(str(e))
            self.logger.error(error_msg)
            self.logger.error('event was: {}'.format(str(message)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.handler_stats.error(self.conf, None)
            self.fail_msg(message)
            return error_msg, 500

        try:
            error_code, response = self.handler.handle(data, activity)
            if error_code == ErrorCodes.OK:
                return response, 200
            else:
                return response, 500
        except InterruptedError:
            error_msg = 'got interrupt, dropping message'.format(str(message.value))
            self.logger.warning(error_msg)
            self.env.handler_stats.failure(self.conf, activity)
            self.drop_msg(message)
            return error_msg, 500
        except Exception as e:
            error_msg = 'got uncaught exception: {}'.format(str(e))
            self.logger.error(error_msg)
            self.logger.error('event was: {}'.format(str(data)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.handler_stats.error(self.conf, activity)
            self.fail_msg(data)
            return error_msg, 500

    def log_pre_processed_request(self, original_topic: str, data: dict):
        log_topic = '{}-preprocessed'.format(original_topic)
        try:
            self.env.kafka_writer.log(log_topic, data)
        except Exception as e:
            self.logger.error('could not publish pre-processed request to kafka: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def try_to_parse(self, data) -> (dict, Activity):
        try:
            enriched_data = self.env.enrichment_manager.handle(data)
        except Exception as e:
            raise ParseException(e)

        try:
            activity = parse_as(enriched_data)
            return enriched_data, activity
        except Exception as e:
            raise ParseException(e)

    def fail_msg(self, message):
        try:
            self.failed_msg_log.info(str(message))
        except Exception as e:
            self.logger.error('could not log failed message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def drop_msg(self, message):
        try:
            self.dropped_msg_log.info(str(message))
        except Exception as e:
            self.logger.error('could not log dropped message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def create_loggers(self):
        def _create_logger(_path: str, _name: str) -> logging.Logger:
            msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
            msg_handler = logging.FileHandler(_path)
            msg_handler.setFormatter(msg_formatter)
            msg_logger = logging.getLogger(_name)
            msg_logger.setLevel(logging.INFO)
            msg_logger.addHandler(msg_handler)
            return msg_logger

        f_msg_path = self.env.config.get(
            ConfigKeys.FAILED_MESSAGE_LOG, default='/tmp/logistik-failed-msgs.log')

        d_msg_path = self.env.config.get(
            ConfigKeys.DROPPED_MESSAGE_LOG, default='/tmp/logistik-dropped-msgs.log')

        self.failed_msg_log = _create_logger(f_msg_path, 'FailedMessages')
        self.dropped_msg_log = _create_logger(d_msg_path, 'DroppedMessages')


class RestReader(IRestReader):
    def __init__(self, env: GNEnvironment, handler_conf: HandlerConf, handler: IHandler):
        self.logger = logging.getLogger(__name__)
        self.env = env
        self.conf: HandlerConf = handler_conf
        self.handler = handler
        self.enabled = True
        self.consumers: List[RestConsumer] = list()

    def get_consumer_config(self):
        return defaultdict(default_factory=str)

    def run(self) -> None:
        if self.conf.event == 'UNMAPPED':
            self.logger.info('not enabling reading for {}, no event mapped'.format(self.conf.node_id()))
            return

        url = '/api/v1/{}'.format(self.conf.reader_endpoint)
        try:
            self.env.api.add_resource(
                RestConsumer,
                url,
                resource_class_kwargs={
                    'conf': self.conf,
                    'env': self.env,
                    'handler': self.handler,
                    'reader': self
                }
            )
        except Exception as e:
            self.logger.info('seems we already have one for {}'.format(url))
            return
        self.logger.info('added rest endpoint {}'.format(url))

    def register_consumer(self, consumer: RestConsumer):
        self.consumers.append(consumer)

    def stop(self):
        for consumer in self.consumers:
            consumer.stop()

    def start(self):
        for consumer in self.consumers:
            consumer.start()
