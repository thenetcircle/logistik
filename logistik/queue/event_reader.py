import json
import logging
import os
import sys
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union

import pytz
from activitystreams import Activity
from activitystreams import parse as parse_as

from logistik.config import ConfigKeys
from logistik.environ import create_env, initialize_env
from logistik.handlers.manager import HandlersManager
from logistik.queue import IKafkaWriter
from logistik.queue.kafka_writer import KafkaWriter
from logistik.utils.exceptions import ParseException

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
    def __init__(self, topic: str, all_handlers: list):
        self.topic = topic

        self.all_handlers = all_handlers
        self.logger = None
        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.reader_factory = None
        self.consumer = None
        self.env = None
        self.handler_manager = None
        self.kafka_writer: IKafkaWriter = None

    def run(self, sleep_time=3, exit_on_failure=False):
        self.create_env()
        self.create_loggers()

        if self.topic == "UNMAPPED":
            self.logger.warning("not enabling reading, topic is UNMAPPED")
            return

        self.create_consumer()
        self.create_event_manager()

        if sleep_time > 0:
            self.logger.info(
                "sleeping for {} second(s) before consuming".format(sleep_time)
            )
            time.sleep(sleep_time)

        while True:
            try:
                self.try_to_read()
            except InterruptedError as e:
                self.logger.info("got interrupted, shutting down...")
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                break
            except Exception as e:
                self.logger.error("could not read from kafka: {}".format(str(e)))
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())

                if exit_on_failure:
                    break

                time.sleep(1)

    def create_consumer(self):
        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        group_id = self.group_id()

        self.logger.info("bootstrapping from servers: %s" % (str(bootstrap_servers)))
        self.logger.info("consuming from topic {} using group_id {}".format(self.topic, group_id))

        self.reader_factory = KafkaReaderFactory()
        self.consumer = self.reader_factory.create_consumer(
            self.topic,
            group_id=group_id,
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=True,
            auto_offset_reset="latest",
            connections_max_idle_ms=9 * ONE_MINUTE,  # default: 9min
            max_poll_interval_ms=10 * ONE_MINUTE,  # default: 5min
            session_timeout_ms=ONE_MINUTE,  # default: 10s
            max_poll_records=50,  # default: 500,
            max_in_flight_requests_per_connection=10,  # default: 5
        )

    def create_event_manager(self):
        event_handlers = list()

        for handler in self.all_handlers:
            if handler.retired or handler.event != self.topic:
                continue

            event_handlers.append(handler)

        self.handler_manager = HandlersManager(self.env)
        self.handler_manager.start_event_handler(self.topic, event_handlers)

    def create_env(self):
        config_paths = None
        if "LK_CONFIG" in os.environ:
            config_paths = [os.environ["LK_CONFIG"]]

        env = create_env(config_paths)
        initialize_env(env, is_parent_process=False)

        self.env = env

    def try_to_read(self):
        for message in self.consumer:
            data = self.try_to_parse(message)
            if data is None:
                continue

            try:
                self.logger.info(f"request: {data}")
                self.handler_manager.handle_event(message.topic, data)
            except Exception as e:
                event_id = data.get("id")[:8]
                self.logger.error(
                    f"[{event_id}] dropping event, could not handle: {str(e)}"
                )
                self.logger.exception(e)

    def try_to_parse(self, message) -> (dict, Activity):
        try:
            data = json.loads(message.value.decode("ascii"))
        except Exception as e:
            self.logger.error(
                "could not decode message from kafka, dropping: {}".format(str(e))
            )
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.dropped_msg_log.info(
                "[{}:{}:{}:key={}] {}".format(
                    message.topic,
                    message.partition,
                    message.offset,
                    message.key,
                    str(message.value),
                )
            )
            return

        try:
            return self.env.enrichment_manager.handle(data)
        except Exception as e:
            return self.fail(e, message, data)

    def group_id(self):
        group_id = self.env.config.get(
            ConfigKeys.GROUP_ID,
            domain=ConfigKeys.KAFKA,
            default=""
        )

        if len(group_id) and not group_id != "$LK_GROUP_ID":
            return group_id

        increment_group_id = self.env.config.get(
            ConfigKeys.INCREMENT_GROUP_ID,
            domain=ConfigKeys.KAFKA,
            default=True
        )

        suffix = ""
        if type(increment_group_id) == bool and increment_group_id:
            suffix = "-" + datetime.utcnow().replace(tzinfo=pytz.utc).strftime("%y%m%d")

        return f"{self.topic}{suffix}"

    def fail(self, e, message, message_value):
        self.logger.error("got uncaught exception: {}".format(str(e)))
        self.logger.error("event was: {}".format(str(message)))
        self.logger.exception(traceback.format_exc())
        self.env.capture_exception(sys.exc_info())
        self.fail_msg(message, message.topic, message_value)

    def fail_msg(
        self,
        message,
        original_topic: Union[str, None],
        decoded_value: Union[dict, None],
    ):
        try:
            self.failed_msg_log.info(str(message))

            # in case even decoding failed, we can't publish back to kafka, something
            # odd happened, so just log to the failed message log...
            if decoded_value is not None:
                fail_topic = f"{original_topic}-failed"
                self.kafka_writer.fail(fail_topic, decoded_value)
        except Exception as e:
            self.logger.error("could not log failed message: {}".format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def drop_msg(self, message, original_topic: str, decoded_value: dict):
        try:
            self.dropped_msg_log.info(str(message))

            if decoded_value is not None:
                fail_topic = f"{original_topic}-failed"
                self.kafka_writer.fail(fail_topic, decoded_value)
        except Exception as e:
            self.logger.error("could not log dropped message: {}".format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def create_loggers(self):
        self.logger = logging.getLogger(__name__)

        f_msg_path = self.env.config.get(
            ConfigKeys.FAILED_MESSAGE_LOG, default="/tmp/logistik-failed-msgs.log"
        )
        d_msg_path = self.env.config.get(
            ConfigKeys.DROPPED_MESSAGE_LOG, default="/tmp/logistik-dropped-msgs.log"
        )

        self.failed_msg_log = EventReader.create_logger(f_msg_path, "FailedMessages")
        self.dropped_msg_log = EventReader.create_logger(d_msg_path, "DroppedMessages")

    @staticmethod
    def create_logger(_path: str, _name: str) -> logging.Logger:
        msg_formatter = logging.Formatter("%(asctime)s: %(message)s")
        msg_handler = logging.FileHandler(_path)
        msg_handler.setFormatter(msg_formatter)
        msg_logger = logging.getLogger(_name)
        msg_logger.setLevel(logging.INFO)
        msg_logger.addHandler(msg_handler)
        return msg_logger
