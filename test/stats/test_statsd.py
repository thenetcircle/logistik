from unittest import TestCase

from logistik.config import ConfigKeys
from logistik.stats.statsd import StatsDService
from test.base import MockEnv


class StatsdTest(TestCase):
    def setUp(self) -> None:
        self.env = MockEnv()
        self.env.config.set(ConfigKeys.HOST, 'mock', domain=ConfigKeys.STATS_SERVICE)
        self.stats = StatsDService(self.env)

    def test_inc(self):
        self.assertFalse('test' in self.stats.statsd.vals)
        self.stats.incr('test')
        self.assertEqual(1, self.stats.statsd.vals['test'])

    def test_decr(self):
        self.assertFalse('test' in self.stats.statsd.vals)
        self.stats.incr('test')
        self.assertEqual(1, self.stats.statsd.vals['test'])
        self.stats.decr('test')
        self.assertEqual(0, self.stats.statsd.vals['test'])

    def test_timing(self):
        float_val = 12.1
        self.assertFalse('test' in self.stats.statsd.timings)
        self.stats.timing('test', float_val)
        self.assertEqual(float_val, self.stats.statsd.timings['test'])

    def test_gauge(self):
        self.assertFalse('test' in self.stats.statsd.vals)
        self.stats.gauge('test', 8)
        self.assertEqual(8, self.stats.statsd.vals['test'])

    def test_set(self):
        self.assertFalse('test' in self.stats.statsd.vals)
        self.stats.set('test', 9)
        self.assertEqual(9, self.stats.statsd.vals['test'])
