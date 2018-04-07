import traceback
import sys

from abc import ABC
from yapsy.IPlugin import IPlugin
from activitystreams import Activity
from logging import Logger

from logistik.config import ErrorCodes
from logistik import environ


class BaseHandler(IPlugin, ABC):
    OK = True
    FAIL = False

    def __init__(self):
        super().__init__()
        self.logger: Logger = None
        self.__enabled: bool = False
        self.__name: str = None

    def __call__(self, *args, **kwargs) -> (bool, str):
        if not self.enabled:
            return

        data, activity = args[0], args[1]
        try:
            response = self.handle(data, activity)
        except Exception as e:
            self.logger.error('could not execute plugin {}: {}'.format(self.name, str(e)))
            self.logger.exception(traceback.format_exc())
            environ.env.capture_exception(sys.exc_info())
            return BaseHandler.FAIL, ErrorCodes.HANDLER_ERROR, 'could not execute handler {}'.format(self.name)

        return BaseHandler.OK, ErrorCodes.OK, response

    def setup(self, env: environ.GNEnvironment):
        raise NotImplementedError('setup() not implemented in plugin')

    def handle(self, data: dict, activity: Activity):
        raise NotImplementedError('handle() not implemented in plugin')

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
