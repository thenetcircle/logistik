from abc import ABC
from abc import abstractmethod


class IStats(ABC):
    @abstractmethod
    def incr(self, key: str) -> None:
        """pass"""

    @abstractmethod
    def decr(self, key: str) -> None:
        """pass"""

    @abstractmethod
    def timing(self, key: str, ms: float):
        """pass"""

    @abstractmethod
    def gauge(self, key: str, value: int):
        """pass"""

    @abstractmethod
    def set(self, key: str, value: int):
        """pass"""
