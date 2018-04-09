from abc import ABC
from typing import List
from logistik.db.repr.handler import HandlerConf
from logistik.db.repr.event import EventConf


class IDatabase(ABC):
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        raise NotImplementedError()

    def get_event_conf_for(self, event_name: str) -> EventConf:
        raise NotImplementedError()
