from abc import ABC, abstractmethod
from requests import Response

from logistik.db.reprs.handler import HandlerConf


class IRestReader(ABC):
    @abstractmethod
    def run(self):
        """pass"""

    @abstractmethod
    def stop(self):
        """pass"""


class IKafkaReader(ABC):
    @abstractmethod
    def run(self):
        """pass"""

    @abstractmethod
    def stop(self):
        """pass"""

    @abstractmethod
    def get_consumer_config(self) -> dict:
        """pass"""


class IKafkaWriter(ABC):
    @abstractmethod
    def fail(self, topic: str, data: dict) -> None:
        """pass"""

    @abstractmethod
    def publish(self, conf: HandlerConf, message: Response) -> None:
        """pass"""
