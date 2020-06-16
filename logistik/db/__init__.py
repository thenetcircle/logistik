from abc import ABC
from abc import abstractmethod
from typing import List, Union

from logistik.db.reprs.handler import HandlerConf


class IDatabase(ABC):
    @abstractmethod
    def get_all_active_handlers(self) -> List[HandlerConf]:
        """pass"""

    @abstractmethod
    def get_all_handlers(self) -> List[HandlerConf]:
        """pass"""

    @abstractmethod
    def update_handler(self, handler_conf: HandlerConf):
        """pass"""
