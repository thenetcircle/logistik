from abc import ABC
from typing import Union

from activitystreams import Activity
from requests import Response

from logistik.config import ErrorCodes
from logistik.db.repr.handler import HandlerConf


class IHandlersManager(ABC):
    def handle(self, data: dict, activity: Activity) -> None:
        """
        handle the event and possible tell the kafka writer to send a response

        :param data: the original event, before being parsed into a activity streams model
        :param activity: the incoming event in activity streams format
        :return: nothing
        """


class IHandler(ABC):
    def configure(self, conf: HandlerConf):
        raise NotImplementedError()

    def setup(self, env):
        raise NotImplementedError('setup() not implemented in plugin')

    def handle_once(self, data: dict, _: Activity) -> (ErrorCodes, Union[None, Response]):
        raise NotImplementedError('handle_once() not implemented in plugin')

    def __call__(self, *args, **kwargs) -> (bool, str):
        raise NotImplementedError()


class IHandlerStats(ABC):
    def failure(self, handler: IHandler, conf: HandlerConf) -> None:
        raise NotImplementedError()

    def success(self, handler: IHandler, conf: HandlerConf) -> None:
        raise NotImplementedError()

    def error(self, handler: IHandler, conf: HandlerConf) -> None:
        raise NotImplementedError()
