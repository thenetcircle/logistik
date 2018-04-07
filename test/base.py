from unittest import TestCase

from logistik.utils.kafka_reader import KafkaReader
from logistik.environ import GNEnvironment
from logistik.environ import ConfigDict
from logistik.stats import StatsBase


class MockLogger(object):
    def __init__(self):
        self.drops = 0

    def info(self, _):
        self.drops += 1

    def warning(self, _):
        self.drops += 1


class MockStats(StatsBase):
    def incr(self, key: str) -> None:
        pass

    def decr(self, key: str) -> None:
        pass

    def timing(self, key: str, ms: float):
        pass

    def gauge(self, key: str, value: int):
        pass

    def set(self, key: str, value: int):
        pass


class MockEnv(GNEnvironment):
    def __init__(self):
        super().__init__(None, ConfigDict(dict()))
        self.dropped_msg_log = MockLogger()
        self.failed_msg_log = MockLogger()
        self.stats = MockStats()


class BaseTest(TestCase):
    def setUp(self):
        self.env = MockEnv()
        self.reader = KafkaReader(self.env)
