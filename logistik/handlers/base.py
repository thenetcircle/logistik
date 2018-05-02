import traceback
import sys

from abc import ABC
from yapsy.IPlugin import IPlugin
from logging import Logger
from activitystreams import Activity
from typing import Union
from requests import Response

from logistik.config import ErrorCodes
from logistik.handlers import IHandler
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
        self.url = None
        self.endpoint: str = None
        self.timeout: int = None
        self.n_retries: int = 1

    def handle(self, data: dict, activity: Activity) -> (ErrorCodes, Union[None, Response]):
        for i in range(self.n_retries):
            try:
                return self.handle_once(data, activity)
            except Exception as e:
                self.logger.error('attempt {}/{} failed for endpoint {}, error was: {}'.format(
                    str(i+1), self.n_retries, self.endpoint, str(e))
                )
                self.logger.exception(e)
                environ.env.capture_exception(sys.exc_info())

        utils.fail_message(data)
        return ErrorCodes.RETRIES_EXCEEDED, None

    def __call__(self, *args, **kwargs) -> (bool, str):
        if not self.enabled:
            return BaseHandler.FAIL, ErrorCodes.UNKNOWN_ERROR, None

        data, activity = args[0], args[1]
        try:
            error_code, response = self.handle(data, activity)
        except Exception as e:
            self.logger.error('could not execute plugin {}: {}'.format(self.name, str(e)))
            self.logger.exception(traceback.format_exc())
            environ.env.capture_exception(sys.exc_info())
            return BaseHandler.FAIL, ErrorCodes.HANDLER_ERROR, 'could not execute handler {}'.format(self.name)

        if ErrorCodes.OK == error_code:
            return BaseHandler.OK, ErrorCodes.OK, response
        else:
            self.logger.error('handler {} failed with code: {}, response: {}'.format(
                str(self), str(error_code), str(response)))
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
