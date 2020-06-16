import logging
import sys
import traceback
from functools import partial
from multiprocessing import Process
from multiprocessing import Manager
import time
from typing import List, Tuple, Any

from activitystreams import Activity
from activitystreams import parse as parse_as

from logistik.db.reprs.handler import HandlerConf
from logistik.handlers.http import HttpHandler
from logistik.handlers.request import Requester
from logistik.queue.kafka_writer import KafkaWriter
from logistik.utils.exceptions import ParseException

ONE_MINUTE = 60_000


class EventHandler:
    def __init__(self, env, topic: str, handlers: list):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.topic = topic
        self.handlers = handlers

        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.consumer = None
        self.kafka_writer = None

        self.create_kafka_writer()

    def create_kafka_writer(self):
        self.kafka_writer = KafkaWriter(self.env)
        self.kafka_writer.setup()

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
            self, activity, data, handlers: list
    ) -> List[Tuple[HandlerConf, dict]]:
        all_responses: List[Tuple[HandlerConf, dict]] = list()
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

                # send successful responses right away, then retry failed ones
                for handler_conf, response in responses:
                    self.kafka_writer.publish(handler_conf, response)

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

            if retry_idx > 0:
                self.logger.info(f"sleeping for {delay:.2f}s before next retry")
                time.sleep(delay)

        return all_responses

    def call_handlers(self, data: dict, handlers) -> (List[Tuple[HandlerConf, dict]], list):
        handler_func = partial(HttpHandler.call_handler, data)
        responses = list()
        failures = list()
        threads = list()

        manager = Manager()
        return_dict = manager.dict()

        for handler in handlers:
            p = Process(target=handler_func, args=(handler, return_dict))
            threads.append((p, handler))

        for p, _ in threads:
            p.start()

        for p, handler in threads:
            try:
                p.join()
            except Exception as e:
                self.logger.error(f"could not handle: {str(e)}")
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                failures.append(handler)

        for handler, (status_code, response) in return_dict.items():
            if status_code not in {200, 422, 404, 400}:  # 'OK', 'Duplicate Request', 'Not Found' and 'Bad Request'
                self.logger.warning(f"got status code {status_code} for handler {handler.node_id()}")
                failures.append(handler)
            else:
                responses.append((handler, response))

        return responses, failures

    @staticmethod
    def call_handler(data: dict, handler_conf):
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
