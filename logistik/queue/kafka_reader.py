import json
import sys
import logging
import time
import traceback
from collections import defaultdict
from uuid import uuid4 as uuid

from kafka import KafkaConsumer
from activitystreams import parse as parse_as
from activitystreams import Activity

from logistik.utils.exceptions import ParseException
from logistik.queue import IKafkaReader
from logistik.config import ConfigKeys, ModelTypes
from logistik.environ import GNEnvironment
from logistik.handlers.base import IHandler
from logistik.db.repr.handler import HandlerConf

logger = logging.getLogger(__name__)
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)

ONE_MINUTE = 60_000


class KafkaReader(IKafkaReader):
    def __init__(self, env: GNEnvironment, handler_conf: HandlerConf, handler: IHandler):
        self.logger = logging.getLogger(__name__)
        self.env = env
        self.conf: HandlerConf = handler_conf
        self.handler = handler
        self.enabled = True
        self.consumer: KafkaConsumer = None
        self.failed_msg_log = None
        self.dropped_msg_log = None

    def run(self) -> None:
        logger.info('sleeping for 3 second before consuming')
        time.sleep(3)

        self.create_loggers()

        def _create_logger(_path: str, _name: str) -> logging.Logger:
            msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
            msg_handler = logging.FileHandler(_path)
            msg_handler.setFormatter(msg_formatter)
            msg_logger = logging.getLogger(_name)
            msg_logger.setLevel(logging.INFO)
            msg_logger.addHandler(msg_handler)
            return msg_logger

        d_msg_path = self.env.config.get(ConfigKeys.DROPPED_MESSAGE_LOG, default='/tmp/logistik-dropped-msgs.log')
        self.dropped_msg_log = _create_logger(d_msg_path, 'DroppedMessages')

        if self.conf.event == 'UNMAPPED':
            self.logger.info('not enabling reading for {}, no event mapped'.format(self.conf.node_id()))
            return

        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        self.logger.info('bootstrapping from servers: %s' % (str(bootstrap_servers)))

        topic_name = self.conf.event
        self.logger.info('consuming from topic {}'.format(topic_name))

        if self.conf.model_type == ModelTypes.CANARY:
            group_id = 'logistik-{}-{}'.format(self.conf.service_id, str(uuid()))
            self.logger.info('canary model using Group ID {} to get all messages'.format(group_id))
        else:
            group_id = 'logistik-{}'.format(self.conf.service_id)

        self.consumer = KafkaConsumer(
            topic_name,
            group_id=group_id,
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=True,
            connections_max_idle_ms=9 * ONE_MINUTE,  # default: 9min
            max_poll_interval_ms=10 * ONE_MINUTE,  # default: 5min
            session_timeout_ms=ONE_MINUTE,  # default: 10s
            max_poll_records=10  # default: 500
        )

        while True:
            if not self.enabled:
                self.logger.info('reader for "{}" disabled, shutting down'.format(self.conf.service_id))
                break

            try:
                self.try_to_read()
            except InterruptedError:
                logger.info('got interrupted, shutting down...')
                break
            except Exception as e:
                logger.error('could not read from kafka: {}'.format(str(e)))
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                time.sleep(1)

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

    def try_to_read(self):
        for message in self.consumer:
            try:
                self.handle_message(message)
            except InterruptedError:
                raise
            except Exception as e:
                self.logger.error('failed to handle message: {}'.format(str(e)))
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                self.fail_msg(message)
                time.sleep(1)

    def get_consumer_config(self):
        if self.consumer is None:
            return defaultdict(default_factory=str)
        return self.consumer.config

    def stop(self):
        self.enabled = False

    def handle_message(self, message) -> None:
        self.logger.debug("%s:%d:%d: key=%s" % (
            message.topic, message.partition,
            message.offset, message.key)
        )

        try:
            message_value = json.loads(message.value.decode('ascii'))
        except Exception as e:
            logger.error('could not decode message from kafka, dropping: {}'.format(str(e)))
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.dropped_msg_log.info("[{}:{}:{}:key={}] {}".format(
                message.topic, message.partition,
                message.offset, message.key, str(message.value))
            )
            return

        try:
            data, activity = self.try_to_parse(message_value)
            self.log_pre_processed_request(message.topic, data)
        except InterruptedError:
            self.logger.warning('got interrupt, dropping message'.format(str(message.value)))
            self.env.handler_stats.failure(self.conf, None)
            self.drop_msg(message, message.topic, message_value)
            raise
        except ParseException:
            self.logger.error('could not enrich/parse data, original data was: {}'.format(str(message.value)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.handler_stats.error(self.conf, None)
            self.fail_msg(message, message.topic, message_value)
            return
        except Exception as e:
            self.logger.error('got uncaught exception: {}'.format(str(e)))
            self.logger.error('event was: {}'.format(str(message)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.handler_stats.error(self.conf, None)
            self.fail_msg(message, message.topic, message_value)
            return

        try:
            self.handler.handle(data, activity)
        except InterruptedError:
            raise
        except Exception as e:
            self.logger.error('got uncaught exception: {}'.format(str(e)))
            self.logger.error('event was: {}'.format(str(data)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.handler_stats.error(self.conf, None)
            self.fail_msg(message, message.topic, message_value)

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

    def log_pre_processed_request(self, original_topic: str, decoded_value: dict):
        try:
            log_topic = f'{original_topic}-preprocessed'
            self.env.kafka_writer.log(log_topic, decoded_value)
        except Exception as e:
            self.logger.error('could not publish pre-processed request to kafka: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def fail_msg(self, message, original_topic: str, decoded_value: dict):
        try:
            self.failed_msg_log.info(str(message))

            fail_topic = f'{original_topic}-failed'
            self.env.kafka_writer.fail(fail_topic, decoded_value)
        except Exception as e:
            self.logger.error('could not log failed message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def drop_msg(self, message, original_topic: str, decoded_value: dict):
        try:
            self.dropped_msg_log.info(str(message))

            drop_topic = f'{original_topic}-dropped'
            self.env.kafka_writer.drop(drop_topic, decoded_value)
        except Exception as e:
            self.logger.error('could not log dropped message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
