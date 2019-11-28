from abc import ABC
from abc import abstractmethod
from typing import Union

from activitystreams import Activity
from requests import Response

from logistik.config import ErrorCodes
from logistik.db.reprs.handler import HandlerConf


class IRequester(ABC):
    @abstractmethod
    def request(self, method, url, data, json_header):
        """pass"""


class IHandlersManager(ABC):
    @abstractmethod
    def setup(self):
        """pass"""

    @abstractmethod
    def start_handler(self, node_id: str) -> None:
        """pass"""

    @abstractmethod
    def stop_handler(self, node_id: str) -> None:
        """pass"""

    @abstractmethod
    def get_handlers(self) -> list:
        """pass"""

    @abstractmethod
    def query_model_for_info(self, handler_conf: HandlerConf):
        """pass"""


class IHandler(ABC):
    @abstractmethod
    def configure(self, conf: HandlerConf):
        """pass"""

    @abstractmethod
    def setup(self, env):
        """pass"""

    @abstractmethod
    def handle_once(self, data: dict, _: Activity, **kwargs) -> (ErrorCodes, Union[None, Response]):
        """pass"""

    @abstractmethod
    def handle(self, data: dict, activity: Activity) -> (bool, str):
        """pass"""

    @abstractmethod
    def stop(self):
        """pass"""
