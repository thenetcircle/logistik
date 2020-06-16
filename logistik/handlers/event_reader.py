import logging
import sys
import json
import time
import traceback
from abc import ABC, abstractmethod

import eventlet
from typing import List, Union, Optional, Tuple
from datetime import datetime
import pytz
from functools import partial

from activitystreams import Activity
from activitystreams import parse as parse_as

from logistik.config import ConfigKeys
from logistik.db import HandlerConf
from logistik import environ
from logistik.handlers.http import HttpHandler
from logistik.handlers.request import Requester
from logistik.utils.exceptions import ParseException
from logistik.utils.exceptions import MaxRetryError

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


class EventReader:
    def __init__(self, topic: str):
        self.env = environ.env
        self.logger = logging.getLogger(__name__)
        self.topic = topic
        self.reader_factory = KafkaReaderFactory()

        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.consumer = None

        if self.topic == 'UNMAPPED':
            self.logger.warning('not enabling reading, topic is UNMAPPED')
            return

        self.create_loggers()
        self.create_consumer()

    def create_consumer(self):
        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)

        self.logger.info('bootstrapping from servers: %s' % (str(bootstrap_servers)))
        self.logger.info('consuming from topic {}'.format(self.topic))

        self.consumer = self.reader_factory.create_consumer(
            self.topic,
            group_id=self.group_id(),
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=True,
            auto_offset_reset='latest',
            connections_max_idle_ms=9 * ONE_MINUTE,  # default: 9min
            max_poll_interval_ms=10 * ONE_MINUTE,  # default: 5min
            session_timeout_ms=ONE_MINUTE,  # default: 10s
            max_poll_records=50  # default: 500
        )

    def run(self, sleep_time=3, exit_on_failure=False):
        if sleep_time > 0:
            self.logger.info('sleeping for {} second before consuming'.format(sleep_time))
            time.sleep(sleep_time)

        while True:
            try:
                self.try_to_read()
            except InterruptedError as e:
                self.logger.info('got interrupted, shutting down...')
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                break
            except Exception as e:
                self.logger.error('could not read from kafka: {}'.format(str(e)))
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())

                if exit_on_failure:
                    break

                time.sleep(1)

    def try_to_read(self):
        for message in self.consumer:
            data = self.try_to_parse(message)
            if data is None:
                continue

            try:
                responses = self.env.handlers_manager.handle_event(message.topic, data)
            except Exception as e:
                event_id = data.get("id")[:8]
                self.logger.error(f"[{event_id}] dropping event, could not handle: {str(e)}")
                continue

            for handler_conf, response in responses:
                self.env.kafka_writer.publish(handler_conf, response)

    def try_to_parse(self, message) -> (dict, Activity):
        self.logger.debug("%s:%d:%d: key=%s" % (
            message.topic, message.partition,
            message.offset, message.key)
        )

        try:
            message_value = json.loads(message.value.decode('ascii'))
        except Exception as e:
            self.logger.error('could not decode message from kafka, dropping: {}'.format(str(e)))
            self.logger.exception(e)
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
            return self.env.enrichment_manager.handle(data)
        except Exception as e:
            return self.fail(e, message, message_value)

    def group_id(self):
        dt = datetime.utcnow().replace(tzinfo=pytz.utc).strftime("%y%m%d")
        return f"{self.topic}-{dt}"

    def fail(self, e, message, message_value):
        self.logger.error('got uncaught exception: {}'.format(str(e)))
        self.logger.error('event was: {}'.format(str(message)))
        self.logger.exception(traceback.format_exc())
        self.env.capture_exception(sys.exc_info())
        self.fail_msg(message, message.topic, message_value)

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

    def create_loggers(self):
        f_msg_path = self.env.config.get(
            ConfigKeys.FAILED_MESSAGE_LOG,
            default='/tmp/logistik-failed-msgs.log'
        )
        d_msg_path = self.env.config.get(
            ConfigKeys.DROPPED_MESSAGE_LOG,
            default='/tmp/logistik-dropped-msgs.log'
        )

        self.failed_msg_log = EventReader.create_logger(f_msg_path, 'FailedMessages')
        self.dropped_msg_log = EventReader.create_logger(d_msg_path, 'DroppedMessages')

    @staticmethod
    def create_logger(_path: str, _name: str) -> logging.Logger:
        msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
        msg_handler = logging.FileHandler(_path)
        msg_handler.setFormatter(msg_formatter)
        msg_logger = logging.getLogger(_name)
        msg_logger.setLevel(logging.INFO)
        msg_logger.addHandler(msg_handler)
        return msg_logger
