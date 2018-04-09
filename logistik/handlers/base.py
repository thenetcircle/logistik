import traceback
import sys

from requests.models import Response
from abc import ABC
from typing import Union
from yapsy.IPlugin import IPlugin
from activitystreams import Activity
from logging import Logger

from logistik.config import ErrorCodes
from logistik.db.models.handler import HandlerConf
from logistik import environ


class BaseHandler(IPlugin, ABC):
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

    def configure(self, conf: HandlerConf):
        self.enabled = conf.enabled
        self.endpoint = conf.endpoint
        self.name = conf.name
        self.version = conf.version
        self.path = conf.path
        self.url = '{}/{}{}'.format(self.endpoint, self.version, self.path)
        self.logger.debug('configured {} with {}'.format(str(self), str(conf)))

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

    def setup(self, env: environ.GNEnvironment):
        raise NotImplementedError('setup() not implemented in plugin')

    def handle(self, data: dict, activity: Activity) -> (ErrorCodes, Union[None, Response]):
        raise NotImplementedError('handle() not implemented in plugin')

    def __str__(self):
        raise NotImplementedError('__str__() not implemented in plugin')

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
