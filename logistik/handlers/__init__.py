from abc import ABC
from abc import abstractmethod
from typing import List

from activitystreams import Activity

from logistik.db import HandlerConf


class IRequester(ABC):
    @staticmethod
    def request(method, url, json=None, headers=None, model=None, timeout=10):
        """pass"""


class IHandlersManager(ABC):
    @abstractmethod
    def start_event_handler(self, event: str, handlers: List[HandlerConf]):
        """pass"""

    @abstractmethod
    def handle_event(self, topic, event) -> List[dict]:
        """pass"""


class IHandler(ABC):
    pass
