import ast
import logging
import sys
import time
import traceback
from functools import partial
from multiprocessing import Manager
from multiprocessing import Process
from typing import List, Optional, Set
from typing import Tuple

from activitystreams import Activity
from activitystreams import parse as parse_as
from requests.models import Response

from logistik.config import ConfigKeys
from logistik.db.reprs.handler import HandlerConf
from logistik.handlers.http import HttpHandler
from logistik.queue.kafka_writer import KafkaWriter
from logistik.utils.exceptions import ParseException

logger = logging.getLogger(__name__)

# don't retry on: 'OK', 'No Content', 'Duplicate Request', 'Not Found' and 'Bad Request'
STATUS_CODES_NOT_TO_RETRY_FOR = {200, 204, 422, 404, 400}
ONE_MINUTE = 60_000


def get_channels_for(activity: Activity) -> Optional[Set]:
    default_response = None

    if not hasattr(activity, "target"):
        return default_response

    target = activity.target
    if not hasattr(target, "content") or not hasattr(target, "object_type"):
        return default_response

    if target.object_type != "channel":
        return default_response

    if target.content is None or len(target.content) == 0:
        return default_response

    try:
        channels = ast.literal_eval(target.content)
    except Exception as e:
        logger.error(f"could not check target.content: {str(e)}")
        logger.error(f"target.content was {target.content}")
        logger.exception(e)
        return default_response

    # evaluating "[]" will have length 0
    if len(channels) == 0 or not type(channels) == list:
        return default_response

    # evaluating "[\"\"]" will have length 1, and first element length 0
    if len(channels) == 1 and len(channels[0]) == 0:
        return default_response

    return set(channels)


class EventHandler:
    def __init__(self, env, topic: str, handlers: List[HandlerConf], tracer):
        self.env = env
        self.topic = topic
        self.handlers = handlers

        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.consumer = None
        self.kafka_writer = None
        self.tracer = tracer

        try:
            self.max_retries = int(float(env.config.get(ConfigKeys.MAX_RETRIES, default=5)))
        except Exception as e:
            logger.error("could not parse max_retries from config, defaulting to 5: {}".format(str(e)))
            self.max_retries = 5

        self.create_kafka_writer()

    def create_kafka_writer(self):
        self.kafka_writer = KafkaWriter(self.env)
        self.kafka_writer.setup()

    def handle_event(self, data, span_ctx=None) -> List[Tuple[HandlerConf, dict]]:
        try:
            activity = self.try_to_parse(data)
        except InterruptedError:
            raise
        except Exception as e:
            logger.error("could not parse data, original data was: {}".format(str(data)))
            logger.exception(e)
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            raise e

        handlers = self.get_handlers_for_request(activity)

        try:
            return self.handle_with_exponential_back_off(activity, data, handlers, span_ctx=span_ctx)
        except Exception as e:
            self.fail(f"could not handle event: {str(e)}", data)
            raise e  # noqa: pycharm thiks this is unreachable

    def get_handlers_for_request(self, activity: Activity):
        """
        target.content could be set to e.g. "[\"pose\",\"gender\"]", to
        not use all models configured for the topic
        """
        channels = get_channels_for(activity)
        all_handlers = self.handlers.copy()

        if channels is None:
            return all_handlers

        handlers = list()
        for handler in all_handlers:
            for channel in channels:
                if channel in handler.group_id:
                    handlers.append(handler)

        logger.info("channels on request: {}".format(channels))
        logger.info("handlers matching channels: {}".format(
            ",".join([handler.group_id for handler in handlers]))
        )

        return handlers

    def handle_with_exponential_back_off(
            self,
            activity,
            data,
            handlers: list,
            span_ctx=None
    ) -> List[Tuple[HandlerConf, dict]]:
        all_responses: List[Tuple[HandlerConf, dict]] = list()
        retry_idx = 0
        delay = 2
        event_id = activity.id[:8]

        if len(handlers):
            topic_name = handlers[0].event
        else:
            topic_name = "<unknown>"

        n_responses_expected = len(handlers)

        while len(all_responses) < n_responses_expected:
            try:
                responses, failures = self.call_handlers(data, handlers, span_ctx=span_ctx)
            except InterruptedError:
                raise
            except Exception as e:
                message = f"[{event_id}] could not call handlers: {str(e)}"
                self.fail(message, data)
                raise e  # noqa: pycharm thinks this is unreachable

            if len(responses):
                all_responses.extend(responses)

                # send successful responses right away, then retry failed ones
                for handler_conf, response in responses:
                    self.kafka_writer.publish(handler_conf, response)

            # handle any potential failures
            if len(failures):
                handlers.clear()

                failed_handler_names = ",".join([handler.name for handler in failures])
                logger.warning(
                    f"[{event_id}] failed handlers: {failed_handler_names}"
                )

                # otherwise it may retry forever, might be an issue with the source image
                if retry_idx > self.max_retries:
                    ok_str = f"[{event_id}] handlers failed too much, dropping event: {failed_handler_names}"
                    self.env.webhook.ok(ok_str, topic_name, event_id)
                    all_responses.extend(failures)
                    continue

                handlers.extend(failures)

                # max delay is 10m, send critical alert
                if delay >= 600:
                    warn_str = f"[{event_id}] handlers still failing after {retry_idx} retries: {failed_handler_names}"
                    self.env.webhook.critical(warn_str, event_id=data.get("id")[:8])
                    delay = 600
                else:
                    delay *= 1.2

                # exponential back-off
                retry_idx += 1
                logger.warning(f"[{event_id}] retry {retry_idx}, delay {delay:.2f}s")
                time.sleep(delay)

        # if there were failures before, send an OK alert
        if retry_idx > 0:
            info_str = f"[{event_id}] all handlers succeeded at retry {retry_idx}"
            logger.info(info_str)
            # self.env.webhook.ok(info_str, topic_name, event_id)

        return all_responses

    def call_handlers(
        self, data: dict, all_handlers: List[HandlerConf], span_ctx=None
    ) -> (List[Tuple[HandlerConf, dict]], list):
        def call_handler(_handler, _return_dict):
            handler_func = partial(HttpHandler.call_handler, data)

            with self.tracer.start_span(operation_name=f"remote:{_handler.name}", child_of=span_ctx) as child_span:
                handler_func(_handler, _return_dict, child_span)

        responses = list()
        failures = list()
        handlers = list()

        for handler in all_handlers:
            cached_response = self.env.cache.get_response_for(handler, data)

            if cached_response is None:
                handlers.append(handler)
            else:
                key = self.env.cache.get_response_key_from_request(handler, data)
                logger.info(f"found cached response for {key}")
                responses.append((handler, cached_response))

        manager = Manager()
        return_dict = manager.dict()

        threads_to_start = list()
        threads_to_join = list()

        # create one process for each http request
        for handler in handlers:
            p = Process(target=call_handler, args=(handler, return_dict))
            threads_to_start.append((p, handler))

        # start all http requests at the same time
        for p, handler in threads_to_start:
            try:
                p.start()
                threads_to_join.append((p, handler))
            except Exception as e:
                logger.error(f"could not start to handle: {str(e)}")
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                failures.append(handler)

        # wait for all models to return responses
        for p, handler in threads_to_join:
            try:
                p.join()
            except Exception as e:
                logger.error(f"could not handle: {str(e)}")
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                failures.append(handler)

        # deal with failures and successes
        for handler, (status_code, response) in return_dict.items():
            dict_response = None

            if type(response) == Response:
                try:
                    dict_response = response.json()
                except Exception as e:
                    logger.error("could not decode response: {}".format(str(e)))
                    logger.exception(e)
                    failures.append(handler)
                    continue

            if status_code not in STATUS_CODES_NOT_TO_RETRY_FOR:
                logger.warning(f"got status code {status_code} for handler {handler.node_id()}")
                failures.append(handler)

            else:
                # only cache successful responses
                if status_code == 200:
                    self.env.cache.set_response_for(handler, data, dict_response)

                responses.append((handler, dict_response))

        # clean-up
        for p, _ in threads_to_start:
            try:
                p.terminate()
            except Exception as e:
                logger.error(f"could not close process: {str(e)}")
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())

        return responses, failures

    def try_to_parse(self, data) -> Activity:
        try:
            return parse_as(data)
        except Exception as e:
            raise ParseException(e)

    def fail(self, message, data) -> None:
        try:
            logger.error(message)
            logger.error(f"request was: {str(data)}")
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            self.env.webhook.critical(message, event_id=data.get("id")[:8])
        except Exception as e:
            logger.error(f"exception in fail(): {str(e)}")
            logger.exception(e)
