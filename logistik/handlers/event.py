import logging
import sys
import json
import time
import traceback
import eventlet
from typing import List, Union
from datetime import datetime
import pytz
from functools import partial

from activitystreams import Activity
from activitystreams import parse as parse_as

from logistik.config import ConfigKeys, ErrorCodes
from logistik.db import HandlerConf
from logistik import environ
from logistik.handlers.http import HttpHandler
from logistik.handlers.request import Requester
from logistik.utils.exceptions import ParseException

ONE_MINUTE = 60_000


class EventHandler:
    def __init__(self, event: str, handlers: List[HandlerConf]):
        environ.initialize_env(environ.env, is_child_process=True)

        # TODO: use two gunicorn instances, one to read events from kafka, and other with workers=10 to handle events

        self.env = environ.env
        self.logger = logging.getLogger(__name__)
        self.event = event
        self.handlers = handlers
        self.running = False
        self.pool = eventlet.GreenPool(len(handlers))

        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.consumer = None

        if self.event == 'UNMAPPED':
            self.logger.info('not enabling reading for {}, no event mapped'.format(self.handlers[0].node_id()))
            return

        self.create_loggers()
        self.create_consumer()

    def create_consumer(self):
        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        topic_name = self.event

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
            max_poll_records=50  # default: 500
        )

    def run(self, sleep_time=3, exit_on_failure=False):
        if sleep_time > 0:
            self.logger.info('sleeping for {} second before consuming'.format(sleep_time))
            time.sleep(sleep_time)

        while True:
            if not self.running:
                self.logger.info('reader for "{}" disabled, shutting down'.format(self.event))
                break

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
            if not self.running:
                self.logger.info(f'stopping consumption of {self.event}')
                time.sleep(0.1)
                break

            try:
                responses = self.handle_message(message)
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

            # TODO: send responses to queue

    def handle_message(self, message) -> Union[None, List[dict]]:
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
            return None

        try:
            data, activity = self.try_to_parse(message_value)
        except InterruptedError:
            raise
        except ParseException:
            self.logger.error('could not enrich/parse data, original data was: {}'.format(str(message.value)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.fail_msg(message, message.topic, message_value)
            return None
        except Exception as e:
            return self.fail(e, message, message_value)

        handlers = self.handlers

        # TODO: only retry failed responses
        try:
            error_code, error_msg, responses = self.call_handlers(data, handlers)
        except InterruptedError:
            raise
        except Exception as e:
            return self.fail(e, message, message_value)

        if error_code != ErrorCodes.OK:
            # TODO: exponential back-off
            # TODO: notify alert channel
            pass

        if error_code == ErrorCodes.RETRIES_EXCEEDED:
            pass

        return responses

    def call_handlers(self, data: dict, handlers) -> (int, str, List[dict]):
        handler_func = partial(HttpHandler.call_handler, data)
        responses = list()

        for response, response_code in self.pool.imap(handler_func, handlers):
            # TODO: handle errors
            self.logger.info(f"code: {response_code}, response: {response}")
            responses.append(response)

        return ErrorCodes.OK, "", responses

    @staticmethod
    def call_handler(data: dict, handler_conf: HandlerConf):
        schema = "http://"
        endpoint = handler_conf.endpoint
        path = handler_conf.path
        method = handler_conf.method
        timeout = handler_conf.timeout
        port = handler_conf.port
        json_header = {"Context-Type": "application/json"}

        if method is None or len(method.strip()) == 0:
            method = "POST"

        separator = ""
        if path is not None and path[0] != "/":
            separator = "/"

        url = "{}{}:{}{}{}".format(
            schema, endpoint, port, separator, path
        )

        response = Requester.request(
            method=method, url=url, json=data, headers=json_header, timeout=timeout
        )

        return response.status_code, response

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

    def group_id(self):
        dt = datetime.utcnow().replace(tzinfo=pytz.utc).strftime("%y%m%d")
        return f"{self.event}-{dt}"

    def stop(self):
        self.running = False

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

        self.failed_msg_log = EventHandler.create_logger(f_msg_path, 'FailedMessages')
        self.dropped_msg_log = EventHandler.create_logger(d_msg_path, 'DroppedMessages')

    @staticmethod
    def create_logger(_path: str, _name: str) -> logging.Logger:
        msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
        msg_handler = logging.FileHandler(_path)
        msg_handler.setFormatter(msg_formatter)
        msg_logger = logging.getLogger(_name)
        msg_logger.setLevel(logging.INFO)
        msg_logger.addHandler(msg_handler)
        return msg_logger
