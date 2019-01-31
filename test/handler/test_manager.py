from unittest import TestCase
from uuid import uuid4 as uuid

from logistik.config import ModelTypes
from logistik.db.repr.handler import HandlerConf
from logistik.handlers.manager import HandlersManager
from test.base import MockEnv


class ManagerTest(TestCase):
    def setUp(self):
        self.manager = HandlersManager(MockEnv())

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
