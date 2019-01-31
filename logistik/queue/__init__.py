from abc import ABC
from requests import Response

from logistik.db.repr.handler import HandlerConf


class IRestReader(ABC):
    def run(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()


class IKafkaReader(ABC):
    def run(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def get_consumer_config(self) -> dict:
        raise NotImplementedError()


class IKafkaWriter(ABC):
    def log(self, topic: str, data: dict) -> None:
        raise NotImplementedError()

    def fail(self, topic: str, data: dict) -> None:
        raise NotImplementedError()

    def drop(self, topic: str, data: dict) -> None:
        raise NotImplementedError()

    def publish(self, conf: HandlerConf, message: Response) -> None:
        raise NotImplementedError()
