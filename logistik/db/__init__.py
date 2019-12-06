from abc import ABC
from abc import abstractmethod
from typing import List, Union

from logistik.db.reprs.handler import HandlerConf


class IDatabase(ABC):
    @abstractmethod
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        """pass"""

    @abstractmethod
    def retire_model(self, node_id: str) -> None:
        """pass"""

    @abstractmethod
    def delete_handler(self, node_id: str) -> None:
        """pass"""

    @abstractmethod
    def demote_model(self, node_id: str) -> Union[HandlerConf, None]:
        """pass"""

    @abstractmethod
    def promote_canary(self, node_id: str) -> Union[HandlerConf, None]:
        """pass"""

    @abstractmethod
    def get_all_handlers(self) -> List[HandlerConf]:
        """pass"""

    @abstractmethod
    def get_all_enabled_handlers(self) -> List[HandlerConf]:
        """pass"""

    @abstractmethod
    def get_handler_for(self, node_id: str) -> HandlerConf:
        """pass"""

    @abstractmethod
    def get_handler_for_identity(self, identity: int) -> HandlerConf:
        """pass"""

    @abstractmethod
    def disable_handler(self, node_id) -> None:
        """pass"""

    @abstractmethod
    def enable_handler(self, node_id) -> None:
        """pass"""

    @abstractmethod
    def find_one_handler(self, service_id, hostname, node) -> Union[HandlerConf, None]:
        """pass"""

    @abstractmethod
    def find_one_similar_handler(self, service_id):
        """pass"""

    @abstractmethod
    def register_handler(self, handler_conf: HandlerConf) -> HandlerConf:
        """pass"""

    @abstractmethod
    def update_consul_service_id_and_group_id(
            self, handler_conf: HandlerConf, consul_service_id: str, tags: dict
    ) -> HandlerConf:
        """pass"""

    @abstractmethod
    def update_handler(self, handler_conf: HandlerConf):
        """pass"""
