import traceback
import sys
import time
import random

from eventlet.greenthread import GreenThread
from abc import ABC
from logging import Logger
from activitystreams import Activity
from typing import Union
from requests import Response

from logistik.config import ErrorCodes
from logistik.config import StatsKeys
from logistik.config import ModelTypes
from logistik.handlers import IHandler


class BaseHandler(IHandler, ABC):
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
        self.env = None
        self.schema: str = None
        self.timeout: int = None
        self.n_retries: int = 1
        self.conf = None
        self.reader = None
        self.reader_thread: GreenThread = None

    def try_to_handle(
        self, data: dict, activity: Activity
    ) -> (ErrorCodes, Union[None, Response]):
        for i in range(self.n_retries):
            try:
                before = time.perf_counter()
                error_code, response = self.handle_once(data, activity)

                if error_code == ErrorCodes.OK:
                    after = time.perf_counter()
                    diff = (after - before) * 1000

                    key = StatsKeys.handler_timing(self.conf.node_id())
                    self.env.stats.timing(key, diff)

                return error_code, response
            except Exception as e:
                self.logger.error(
                    "attempt {}/{} failed for endpoint {}, error was: {}".format(
                        str(i + 1), self.n_retries, self.endpoint, str(e)
                    )
                )
                self.env.capture_exception(sys.exc_info())

        return ErrorCodes.RETRIES_EXCEEDED, None

    def is_canary_and_should_skip(self):
        if self.conf.model_type != ModelTypes.CANARY:
            return False

        # only handle part of the traffic for canary models
        r = random.randint(0, 99)
        traffic = int(self.conf.traffic * 100)

        if r > traffic:
            self.logger.debug(
                "dice shows {}, traffic is {}, skipping event".format(r, traffic)
            )
            return True

        self.logger.debug(
            "dice shows {}, traffic is {}, processing event".format(r, traffic)
        )
        return False

    def handle(self, data: dict, activity: Activity):
        if self.is_canary_and_should_skip():
            return ErrorCodes.OK, "skipped, canary"

        status_code, error_code, response = self.handle_and_return_response(
            data, activity
        )

        if error_code == ErrorCodes.RETRIES_EXCEEDED:
            error_msg = "exceeded max retries, disabling handler"
            self.logger.info(error_msg)
            self.env.kafka_writer.fail(self.conf.failed_topic, data)
            return ErrorCodes.RETRIES_EXCEEDED, error_msg

        # models can choose to ignore requests
        if error_code == ErrorCodes.NO_CONTENT:
            return ErrorCodes.OK, None

        # models can return this code if they've already processed this request
        if error_code == ErrorCodes.DUPLICATE_REQUEST:
            return ErrorCodes.OK, None

        if response is None:
            error_msg = (
                f'empty response event ID "{activity.id}": error_code={error_code}'
            )
            self.logger.warning(error_msg)
            self.env.kafka_writer.fail(self.conf.failed_topic, data)
            return ErrorCodes.HANDLER_ERROR, error_msg

        if status_code == BaseHandler.OK:
            self.env.kafka_writer.publish(self.conf, response)
            return ErrorCodes.OK, response

        else:
            error_msg = f"not publishing response since request failed: {response}"
            self.logger.error(error_msg)
            self.env.kafka_writer.fail(self.conf.failed_topic, data)
            return ErrorCodes.HANDLER_ERROR, response

    def handle_and_return_response(
        self, data: dict, activity: Activity
    ) -> (bool, str, Response):
        if not self.enabled:
            return BaseHandler.FAIL, ErrorCodes.HANDLER_DISABLED, None

        try:
            error_code, response = self.try_to_handle(data, activity)
        except Exception as e:
            self.logger.error(f"could not execute handler {self.name}: {str(e)}")
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return (
                BaseHandler.FAIL,
                ErrorCodes.HANDLER_ERROR,
                f"could not execute handler {self.name}",
            )

        if error_code in {
            ErrorCodes.OK,
            ErrorCodes.NO_CONTENT,
            ErrorCodes.DUPLICATE_REQUEST,
            ErrorCodes.NOT_FOUND,
        }:
            return BaseHandler.OK, error_code, response
        else:
            self.logger.error(
                f"handler {str(self)} failed with code: {error_code}, response: {str(response)}"
            )
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
