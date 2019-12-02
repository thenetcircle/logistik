from abc import ABC
from abc import abstractmethod


class IEnrichmentManager(ABC):
    @abstractmethod
    def handle(self, data: dict) -> dict:
        """pass"""


class IEnricher(ABC):
    @abstractmethod
    def __call__(self, *args, **kwargs) -> dict:
        """pass"""
