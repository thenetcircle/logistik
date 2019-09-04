import traceback
import sys
import time
import random

from eventlet.greenthread import GreenThread
from abc import ABC
from yapsy.IPlugin import IPlugin
from logging import Logger
from activitystreams import Activity
from typing import Union
from requests import Response

from logistik.config import ErrorCodes
from logistik.config import StatsKeys
from logistik.config import ModelTypes
from logistik.handlers import IHandler
from logistik.handlers import HandlerConf
from logistik import environ
from logistik import utils


class BaseHandler(IHandler, IPlugin, ABC):
    OK = True
    FAIL = False

    def __init__(self):
        super().__init__()
        self.logger: Logger = None
        self.__enabled: bool = False
        self.__name: str = None
        self.endpoint = None
        self.version = None
        self.path = None
        self.port = None
        self.url = None
        self.endpoint: str = None
        self.schema: str = None
        self.timeout: int = None
        self.n_retries: int = 1
        self.conf: HandlerConf = None
        self.reader = None
        self.reader_thread: GreenThread = None

    def try_to_handle(self, data: dict, activity: Activity) -> (ErrorCodes, Union[None, Response]):
        for i in range(self.n_retries):
            try:
                before = time.perf_counter()
                error_code, response = self.handle_once(data, activity)

                if error_code == ErrorCodes.OK:
                    after = time.perf_counter()
                    diff = (after-before) * 1000

                    key = StatsKeys.handler_timing(self.conf.node_id())

                    environ.env.stats.timing(key, diff)
                    environ.env.db.register_runtime(self.conf, diff)

                return error_code, response
            except Exception as e:
                self.logger.error('attempt {}/{} failed for endpoint {}, error was: {}'.format(
                    str(i+1), self.n_retries, self.endpoint, str(e))
                )

        utils.fail_message(data)
        return ErrorCodes.RETRIES_EXCEEDED, None

    def is_canary(self):
        return self.conf.model_type == ModelTypes.CANARY

    def handle(self, data: dict, activity: Activity):
        if self.is_canary():
            # only handle part of the traffic for canary models
            r = random.randint(0, 99)

            if r > self.conf.traffic * 100:
                self.logger.debug(
                    'dice shows {}, traffic is {}, skipping event'
                    .format(r, int(self.conf.traffic*100)))

                return ErrorCodes.OK, 'skipped, canary'

            self.logger.debug(
                'dice shows {}, traffic is {}, processing event'
                .format(r, int(self.conf.traffic*100)))

        status_code, error_code, response = self.handle_and_return_response(data, activity)

        if error_code == ErrorCodes.RETRIES_EXCEEDED:
            error_msg = 'exceeded max retries, disabling handler'
            self.logger.info(error_code)
            return ErrorCodes.RETRIES_EXCEEDED, error_msg

        if response is None:
            error_msg = 'empty response for handling event ID "{}": error_code={}'.format(activity.id, error_code)
            self.logger.warning(error_msg)
            return ErrorCodes.HANDLER_ERROR, error_msg

        elif status_code == BaseHandler.OK:
            environ.env.kafka_writer.publish(self.conf, response)
            return ErrorCodes.OK, response

        else:
            error_msg = 'not publishing response since request failed: {}'.format(response)
            self.logger.error(error_msg)
            return ErrorCodes.HANDLER_ERROR, error_msg

    def handle_and_return_response(self, data: dict, activity: Activity) -> (bool, str, Response):
        if not self.enabled:
            environ.env.handler_stats.failure(self.conf, activity)
            return BaseHandler.FAIL, ErrorCodes.HANDLER_DISABLED, None

        try:
            error_code, response = self.try_to_handle(data, activity)
        except Exception as e:
            self.logger.error('could not execute handler {}: {}'.format(self.name, str(e)))
            self.logger.exception(traceback.format_exc())
            environ.env.capture_exception(sys.exc_info())
            environ.env.handler_stats.failure(self.conf, activity)
            return BaseHandler.FAIL, ErrorCodes.HANDLER_ERROR, 'could not execute handler {}'.format(self.name)

        if error_code == ErrorCodes.OK:
            environ.env.handler_stats.success(self.conf, activity)
            return BaseHandler.OK, ErrorCodes.OK, response
        else:
            self.logger.error('handler {} failed with code: {}, response: {}'.format(
                str(self), str(error_code), str(response)))
            environ.env.handler_stats.failure(self.conf, activity)
            return BaseHandler.FAIL, error_code, response

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name

    @property
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self.__enabled = enabled
