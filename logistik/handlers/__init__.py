from abc import ABC
from typing import Union

from activitystreams import Activity
from requests import Response

from logistik.config import ErrorCodes
from logistik.db.repr.handler import HandlerConf


class IHandlersManager(ABC):
    def setup(self):
        raise NotImplementedError()

    def start_handler(self, node_id: str) -> None:
        raise NotImplementedError()

    def stop_handler(self, node_id: str) -> None:
        raise NotImplementedError()

    def get_handlers(self) -> list:
        raise NotImplementedError()


class IHandler(ABC):
    def configure(self, conf: HandlerConf):
        raise NotImplementedError()

    def setup(self, env):
        raise NotImplementedError('setup() not implemented in plugin')

    def handle_once(self, data: dict, _: Activity) -> (ErrorCodes, Union[None, Response]):
        raise NotImplementedError('handle_once() not implemented in plugin')

    def handle(self, data: dict, activity: Activity) -> (bool, str):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()


class IHandlerStats(ABC):
    def failure(self, event: Activity, conf: HandlerConf) -> None:
        raise NotImplementedError()

    def success(self, event: Activity, conf: HandlerConf) -> None:
        raise NotImplementedError()

    def error(self, event: Activity, conf: HandlerConf) -> None:
        raise NotImplementedError()
