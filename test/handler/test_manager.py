from unittest import TestCase
from uuid import uuid4 as uuid

from logistik.config import ModelTypes
from logistik.db.reprs.handler import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from logistik.handlers.manager import HandlersManager
from test.base import MockEnv, MockStats, MockWriter
from test.discover.test_manager import MockCache, MockDb


class ManagerTest(TestCase):
    def setUp(self):
        self.db = MockDb()
        self.cache = MockCache()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        self.env.kafka_writer = MockWriter()
        self.env.stats = MockStats()

        self.manager = HandlersManager(self.env)

    def test_get_handler_configs(self):
        all_confs = list()
        for _ in range(10):
            all_confs.append(HandlerConf(model_type=ModelTypes.MODEL, reader_type='mock', service_id=str(uuid())))
        all_confs.append(HandlerConf(model_type=ModelTypes.CANARY, reader_type='mock', service_id=str(uuid())))
        all_confs.append(HandlerConf(model_type=ModelTypes.DECOY, reader_type='mock', service_id=str(uuid())))

        for conf in all_confs:
            self.manager.add_handler(conf)

        handler_configs = self.manager.get_handlers()
        self.assertEqual(12, len(handler_configs))

    def test_setup(self):
        all_confs = list()
        for _ in range(10):
            all_confs.append(HandlerConf(model_type=ModelTypes.MODEL, reader_type='mock', service_id=str(uuid())))
        all_confs.append(HandlerConf(model_type=ModelTypes.CANARY, reader_type='mock', service_id=str(uuid())))
        all_confs.append(HandlerConf(model_type=ModelTypes.DECOY, reader_type='mock', service_id=str(uuid())))

        for conf in all_confs:
            self.manager.add_handler(conf)

        self.manager.setup()
        handler_configs = self.manager.get_handlers()
        self.assertEqual(12, len(handler_configs))
