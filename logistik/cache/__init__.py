from abc import ABC
from abc import abstractmethod

from typing import List
from logistik.db.reprs.handler import HandlerConf


class ICache(ABC):
    @abstractmethod
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        """pass"""

    @abstractmethod
    def reset_enabled_handlers_for(self, event_name: str) -> None:
        """pass"""

    @abstractmethod
    def set_enabled_handlers_for(self, event_name: str, handlers: List[HandlerConf]):
        """pass"""
