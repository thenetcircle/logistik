from abc import ABC
from abc import abstractmethod
from typing import List

from activitystreams import Activity

from logistik.db import HandlerConf


class IRequester(ABC):
    @staticmethod
    def request(method, url, json=None, headers=None):
        """pass"""


class IHandlersManager(ABC):
    @abstractmethod
    def start_event_handler(self, event: str, handlers: List[HandlerConf]):
        """pass"""

    @abstractmethod
    def query_model_for_info(self, handler_conf):
        """pass"""

    @abstractmethod
    def handle_event(self, topic, event) -> List[dict]:
        """pass"""


class IHandler(ABC):
    @abstractmethod
    def configure(self, conf):
        """pass"""

    @abstractmethod
    def setup(self, env):
        """pass"""

    @abstractmethod
    def handle_once(self, data: dict, _: Activity, **kwargs) -> tuple:
        """pass"""

    @abstractmethod
    def handle(self, data: dict, activity: Activity) -> (bool, str):
        """pass"""

    @abstractmethod
    def stop(self):
        """pass"""
