import logging
import sys
import traceback
from functools import partial
from typing import List, Optional, Tuple, Union

import eventlet
from activitystreams import Activity
from activitystreams import parse as parse_as

from logistik import environ
from logistik.db import HandlerConf
from logistik.handlers.http import HttpHandler
from logistik.handlers.request import Requester
from logistik.utils.exceptions import ParseException

ONE_MINUTE = 60_000


class EventHandler:
    def __init__(self, env, topic: str, handlers: List[HandlerConf]):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.topic = topic
        self.handlers = handlers
        self.running = False
        self.pool = eventlet.GreenPool(len(handlers))

        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.consumer = None

        if self.topic == 'UNMAPPED':
            self.logger.info('not enabling reading for {}, no topic mapped'.format(self.handlers[0].node_id()))

    def handle_event(self, data) -> List[dict]:
        try:
            activity = self.try_to_parse(data)
        except InterruptedError:
            raise
        except Exception as e:
            self.logger.error('could not parse data, original data was: {}'.format(str(data)))
            self.logger.exception(e)
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            raise e

        handlers = self.handlers.copy()

        try:
            responses = self.handle_with_exponential_back_off(activity, data, handlers)
        except Exception as e:
            self.fail(f"could not handle event: {str(e)}", data)
            raise e

        return responses

    def handle_with_exponential_back_off(
            self, activity, data, handlers: List[HandlerConf]
    ) -> List[dict]:
        all_responses = list()
        retry_idx = 0
        delay = 2
        event_id = activity.id[:8]

        if len(handlers):
            topic_name = handlers[0].event
        else:
            topic_name = '<unknown>'

        while len(all_responses) < len(handlers):
            try:
                responses, failures = self.call_handlers(data, handlers)
            except InterruptedError:
                raise
            except Exception as e:
                message = f"could not call handlers: {str(e)}"
                self.fail(message, data)
                raise e

            if len(responses):
                all_responses.extend(responses)

            if len(failures):
                handlers.clear()
                handlers.extend(failures)

                failed_handler_names = ",".join([handler.name for handler in handlers])
                self.logger.warning(f"[{event_id}] failed handlers: {failed_handler_names}")
                self.logger.warning(f"[{event_id}] retry {retry_idx}, delay {delay:.2f}s")

                if retry_idx == 0:
                    warning_str = f"handlers failed: {failed_handler_names}"
                    self.env.webhook.warning(warning_str, topic_name, event_id)

                if delay >= 600:
                    warning_str = f"handlers still failing after {retry_idx} retries: {failed_handler_names}"
                    self.env.webhook.critical(warning_str, event_id=data.get("id")[:8])
                    delay = 600
                else:
                    delay *= 1.2

                retry_idx += 1

            elif retry_idx > 0:
                info_str = f"[{event_id}] all handlers succeeded at retry {retry_idx}"
                self.env.webhook.ok(info_str, topic_name, event_id)
                self.logger.info(info_str)
                break

        return all_responses

    def call_handlers(self, data: dict, handlers) -> (List[dict], List[HandlerConf]):
        handler_func = partial(HttpHandler.call_handler, data)
        responses: List[dict] = list()
        failures: List[HandlerConf] = list()
        threads = list()

        for handler in handlers:
            p = eventlet.spawn(handler_func, handler)
            threads.append((p, handler))

        for p, handler in threads:
            try:
                response = p.wait()
                responses.append(response)
            except Exception as e:
                self.logger.error(f"could not handle: {str(e)}")
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                failures.append(handler)

        return responses, failures

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

    def try_to_parse(self, data) -> Activity:
        try:
            return parse_as(data)
        except Exception as e:
            raise ParseException(e)

    def fail(self, message, data) -> None:
        try:
            self.logger.error(message)
            self.logger.error(f"request was: {str(data)}")
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.webhook.critical(message, event_id=data.get("id")[:8])
        except Exception as e:
            self.logger.error(f"exception in fail(): {str(e)}")
            self.logger.exception(e)
