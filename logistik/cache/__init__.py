from abc import ABC

from typing import List
from logistik.db.reprs.handler import HandlerConf


class ICache(ABC):
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        raise NotImplementedError()

    def reset_enabled_handlers_for(self, event_name: str) -> None:
        raise NotImplementedError()

    def set_enabled_handlers_for(self, event_name: str, handlers: List[HandlerConf]):
        raise NotImplementedError()
