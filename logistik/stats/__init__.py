from abc import ABC


class IStats(ABC):
    def incr(self, key: str) -> None:
        raise NotImplementedError()

    def decr(self, key: str) -> None:
        raise NotImplementedError()

    def timing(self, key: str, ms: float):
        raise NotImplementedError()

    def gauge(self, key: str, value: int):
        raise NotImplementedError()

    def set(self, key: str, value: int):
        raise NotImplementedError()
