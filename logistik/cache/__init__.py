from abc import ABC

from logistik.db import HandlerConf


class ICache(ABC):
    def set_response_for(self, handler: HandlerConf, request: dict, response: dict) -> None:
        pass

    def get_response_for(self, handler: HandlerConf, request: dict) -> dict:
        pass
