from abc import ABC
from abc import abstractmethod
from typing import List, Union

from logistik.db.reprs.agg_stats import AggregatedHandlerStats
from logistik.db.reprs.agg_timing import AggTiming
from logistik.db.reprs.handler import HandlerConf
from logistik.db.reprs.event import EventConf


class IDatabase(ABC):
    @abstractmethod
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        pass

    @abstractmethod
    def get_event_conf_for(self, event_name: str) -> EventConf:
        pass

    @abstractmethod
    def register_runtime(self, conf: HandlerConf, time_ms: float) -> None:
        pass

    @abstractmethod
    def retire_model(self, node_id: str) -> None:
        pass

    @abstractmethod
    def delete_handler(self, node_id: str) -> None:
        pass

    @abstractmethod
    def demote_model(self, node_id: str) -> Union[HandlerConf, None]:
        pass

    @abstractmethod
    def promote_canary(self, node_id: str) -> Union[HandlerConf, None]:
        pass

    @abstractmethod
    def get_all_handlers(self) -> List[HandlerConf]:
        pass

    @abstractmethod
    def get_all_enabled_handlers(self) -> List[HandlerConf]:
        pass

    @abstractmethod
    def get_handler_for(self, node_id: str) -> HandlerConf:
        pass

    @abstractmethod
    def disable_handler(self, node_id) -> None:
        pass

    @abstractmethod
    def enable_handler(self, node_id) -> None:
        pass

    @abstractmethod
    def find_one_handler(self, service_id, hostname, node) -> Union[HandlerConf, None]:
        pass

    @abstractmethod
    def find_one_similar_handler(self, service_id):
        pass

    @abstractmethod
    def register_handler(self, handler_conf: HandlerConf) -> HandlerConf:
        pass

    @abstractmethod
    def timing_per_node(self) -> dict:
        pass

    @abstractmethod
    def agg_timing_per_node(self) -> dict:
        pass

    @abstractmethod
    def timing_per_service(self) -> dict:
        pass

    @abstractmethod
    def agg_timing_per_service(self) -> dict:
        pass

    @abstractmethod
    def get_all_aggregated_stats(self) -> List[dict]:
        pass

    @abstractmethod
    def handler_stats_per_service(self) -> List[dict]:
        pass

    @abstractmethod
    def timing_per_host_and_version(self) -> List[dict]:
        pass

    @abstractmethod
    def agg_timing_per_host_and_version(self) -> List[dict]:
        pass

    @abstractmethod
    def save_aggregated_timing_entity(self, timing: AggTiming) -> None:
        pass

    @abstractmethod
    def remove_old_timings(self, timing: AggTiming) -> None:
        pass

    @abstractmethod
    def save_aggregated_stats_entity(self, stats: AggregatedHandlerStats) -> None:
        pass

    @abstractmethod
    def remove_old_handler_stats(self, stats: AggregatedHandlerStats) -> None:
        pass

    @abstractmethod
    def update_consul_service_id_and_group_id(
            self, handler_conf: HandlerConf, consul_service_id: str, tags: dict
    ) -> HandlerConf:
        pass

    @abstractmethod
    def update_handler(self, handler_conf: HandlerConf):
        pass
