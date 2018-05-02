from unittest import TestCase
from test.base import MockEnv

from logistik.db.repr.event import EventConf
from logistik.db.repr.handler import HandlerConf
from logistik.cache.redis import CacheRedis


class TestRedisCache(TestCase):
    def setUp(self):
        self.env = MockEnv()
        self.cache = CacheRedis(self.env, host='mock')

    def test_get_handler_for_non_existing_event(self):
        self.cache.set_enabled_handlers_for('existing', [HandlerConf()])
        self.assertIsNone(self.cache.get_enabled_handlers_for('non-existing'))

    def test_get_handler_for_existing_event(self):
        self.cache.set_enabled_handlers_for('existing', [HandlerConf()])
        self.assertIsNotNone(self.cache.get_enabled_handlers_for('existing'))

    def test_set_enabled_handlers(self):
        self.assertIsNone(self.cache.get_enabled_handlers_for('existing'))
        self.cache.set_enabled_handlers_for('existing', [HandlerConf()])
        self.assertIsNotNone(self.cache.get_enabled_handlers_for('existing'))

    def test_get_event_conf_non_existing(self):
        self.assertIsNone(self.cache.get_event_conf_for('non-existing'))

    def test_set_event_conf_existing(self):
        self.assertIsNone(self.cache.get_event_conf_for('existing'))
        self.cache.set_event_conf_for('existing', EventConf())
        self.assertIsNotNone(self.cache.get_event_conf_for('existing'))

    def test_get_event_conf_existing(self):
        self.cache.set_event_conf_for('existing', EventConf())
        self.assertIsNotNone(self.cache.get_event_conf_for('existing'))
