from abc import ABC
from requests import Response

from logistik.db.repr.handler import HandlerConf


class IKafkaReader(ABC):
    def run(self):
        raise NotImplementedError()


class IKafkaWriter(ABC):
    def publish(self, conf: HandlerConf, message: Response) -> None:
        raise NotImplementedError()
