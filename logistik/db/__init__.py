from abc import ABC
from typing import List, Union
from logistik.db.repr.handler import HandlerConf
from logistik.db.repr.event import EventConf


class IDatabase(ABC):
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        raise NotImplementedError()

    def get_event_conf_for(self, event_name: str) -> EventConf:
        raise NotImplementedError()

    def register_runtime(self, conf: HandlerConf, time_ms: float) -> None:
        raise NotImplementedError()

    def demote_model(self, node_id: str) -> Union[HandlerConf, None]:
        raise NotImplementedError()

    def promote_canary(self, node_id: str) -> Union[HandlerConf, None]:
        raise NotImplementedError()

    def get_all_handlers(self) -> List[HandlerConf]:
        raise NotImplementedError()

    def get_all_enabled_handlers(self) -> List[HandlerConf]:
        raise NotImplementedError()

    def get_handler_for(self, node_id: str) -> HandlerConf:
        raise NotImplementedError()

    def disable_handler(self, node_id) -> None:
        raise NotImplementedError()

    def enable_handler(self, node_id) -> None:
        raise NotImplementedError()

    def retire_handler(self, node_id) -> None:
        raise NotImplementedError()

    def find_one_handler(self, service_id, hostname, node) -> Union[HandlerConf, None]:
        raise NotImplementedError()

    def find_one_similar_handler(self, service_id):
        raise NotImplementedError()

    def register_handler(self, handler_conf: HandlerConf) -> HandlerConf:
        raise NotImplementedError()

    def timing_per_node(self) -> dict:
        raise NotImplementedError()

    def timing_per_service(self) -> dict:
        raise NotImplementedError()

    def timing_per_host_and_version(self) -> list:
        raise NotImplementedError()
