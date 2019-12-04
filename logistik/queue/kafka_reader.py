import json
import logging
import sys
import time
import traceback
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from typing import Union
from uuid import uuid4 as uuid
import multiprocessing

from activitystreams import Activity
from activitystreams import parse as parse_as

from logistik.config import ConfigKeys, ModelTypes, ErrorCodes, HandlerTypes
from logistik.db.reprs.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.handlers.base import IHandler
from logistik.queue import IKafkaReader
from logistik.utils.exceptions import ParseException

logger = logging.getLogger(__name__)
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)

ONE_MINUTE = 60_000


class IKafkaReaderFactory(ABC):
    @abstractmethod
    def create_consumer(self, *args, **kwargs):
        """pass"""


class KafkaReaderFactory(IKafkaReaderFactory):
    """
    for mocking purposes
    """
    def create_consumer(self, *args, **kwargs):
        from kafka import KafkaConsumer
        return KafkaConsumer(*args, **kwargs)


class KafkaReader(IKafkaReader, multiprocessing.Process):
    def __init__(self, env: GNEnvironment, handler_conf: HandlerConf, handler: IHandler, handler_type: str = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.env = env
        self.handler_type = handler_type
        self.conf: HandlerConf = handler_conf
        self.handler = handler
        self.enabled = True
        self.consumer = None
        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.reader_factory = KafkaReaderFactory()

    def run(self, sleep_time=3, exit_on_failure=False) -> None:
        if self.conf.event == 'UNMAPPED':
            self.logger.info('not enabling reading for {}, no event mapped'.format(self.conf.node_id()))
            return

        self.create_loggers()
        self.create_consumer()
        self.start_consuming(sleep_time=sleep_time, exit_on_failure=exit_on_failure)

    def create_consumer(self):
        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        topic_name = self.conf.event

        if self.handler_type is not None and self.handler_type != HandlerTypes.DEFAULT:
            topic_name = f'{topic_name}-{self.handler_type}'

        self.logger.info('bootstrapping from servers: %s' % (str(bootstrap_servers)))
        self.logger.info('consuming from topic {}'.format(topic_name))

        self.consumer = self.reader_factory.create_consumer(
            topic_name,
            group_id=self.group_id(),
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=True,
            auto_offset_reset='latest',
            connections_max_idle_ms=9 * ONE_MINUTE,  # default: 9min
            max_poll_interval_ms=10 * ONE_MINUTE,  # default: 5min
            session_timeout_ms=ONE_MINUTE,  # default: 10s
            max_poll_records=10  # default: 500
        )

    def start_consuming(self, sleep_time=3, exit_on_failure=False):
        if sleep_time > 0:
            logger.info('sleeping for {} second before consuming'.format(sleep_time))
            time.sleep(sleep_time)

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

                if exit_on_failure:
                    break

                time.sleep(1)

    def group_id(self):
        if self.conf.model_type == ModelTypes.CANARY:
            group_id = 'logistik-{}-{}'.format(self.conf.build_group_id(), str(uuid()))
            self.logger.info('canary model using Group ID {} to get all messages'.format(group_id))
        else:
            group_id = 'logistik-{}'.format(self.conf.build_group_id())

        return group_id

    def try_to_read(self):
        for message in self.consumer:
            if not self.enabled:
                logger.info(f'stopping consumption of {self.conf.node_id()}')
                time.sleep(0.1)
                break

            try:
                self.handle_message(message)
            except InterruptedError:
                self.logger.warning('got interrupt, dropping message'.format(str(message.value)))
                self.drop_msg(message, message.topic, json.loads(message.value.decode('ascii')))
                raise
            except Exception as e:
                self.logger.error('failed to handle message: {}'.format(str(e)))
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                self.fail_msg(message, original_topic=None, decoded_value=None)
                time.sleep(1)

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
        except InterruptedError:
            raise
        except ParseException:
            self.logger.error('could not enrich/parse data, original data was: {}'.format(str(message.value)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.fail_msg(message, message.topic, message_value)
            return
        except Exception as e:
            return self.fail(e, message, message_value)

        try:
            error_code, error_msg = self.handler.handle(data, activity)
        except InterruptedError:
            raise
        except Exception as e:
            return self.fail(e, message, message_value)

        if error_code == ErrorCodes.RETRIES_EXCEEDED:
            node_id = self.conf.node_id()
            self.env.db.disable_handler(node_id)
            self.env.handlers_manager.stop_handler(node_id)
            self.stop()

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

    def fail(self, e, message, message_value):
        self.logger.error('got uncaught exception: {}'.format(str(e)))
        self.logger.error('event was: {}'.format(str(message)))
        self.logger.exception(traceback.format_exc())
        self.env.capture_exception(sys.exc_info())
        self.fail_msg(message, message.topic, message_value)

    @staticmethod
    def create_logger(_path: str, _name: str) -> logging.Logger:
        msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
        msg_handler = logging.FileHandler(_path)
        msg_handler.setFormatter(msg_formatter)
        msg_logger = logging.getLogger(_name)
        msg_logger.setLevel(logging.INFO)
        msg_logger.addHandler(msg_handler)
        return msg_logger

    def create_loggers(self):
        f_msg_path = self.env.config.get(
            ConfigKeys.FAILED_MESSAGE_LOG,
            default='/tmp/logistik-failed-msgs.log'
        )
        d_msg_path = self.env.config.get(
            ConfigKeys.DROPPED_MESSAGE_LOG,
            default='/tmp/logistik-dropped-msgs.log'
        )

        self.failed_msg_log = KafkaReader.create_logger(f_msg_path, 'FailedMessages')
        self.dropped_msg_log = KafkaReader.create_logger(d_msg_path, 'DroppedMessages')

    def get_consumer_config(self):
        if self.consumer is None:
            return defaultdict(default_factory=str)
        return self.consumer.config

    def stop(self):
        self.enabled = False

    def fail_msg(self, message, original_topic: Union[str, None], decoded_value: Union[dict, None]):
        try:
            self.failed_msg_log.info(str(message))

            # in case even decoding failed, we can't publish back to kafka, something
            # odd happened, so just log to the failed message log...
            if decoded_value is not None:
                fail_topic = f'{original_topic}-failed'
                self.env.kafka_writer.fail(fail_topic, decoded_value)
        except Exception as e:
            self.logger.error('could not log failed message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def drop_msg(self, message, original_topic: str, decoded_value: dict):
        try:
            self.dropped_msg_log.info(str(message))

            if decoded_value is not None:
                fail_topic = f'{original_topic}-failed'
                self.env.kafka_writer.fail(fail_topic, decoded_value)
        except Exception as e:
            self.logger.error('could not log dropped message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
