from unittest import TestCase

from logistik.handlers.manager import HandlersManager
from logistik.db.repr.handler import HandlerConf
from logistik.config import ModelTypes
from test.base import MockEnv


class ManagerTest(TestCase):
    def setUp(self):
        self.manager = HandlersManager(MockEnv())

    def test_get_handler_configs(self):
        all_confs = list()
        for _ in range(10):
            all_confs.append(HandlerConf(model_type=ModelTypes.MODEL))
        all_confs.append(HandlerConf(model_type=ModelTypes.CANARY))
        all_confs.append(HandlerConf(model_type=ModelTypes.DECOY))

        handlers, canary, decoy = self.manager.get_handler_configs(all_confs)
        self.assertEqual(10, len(handlers))
        self.assertIsNotNone(canary)
        self.assertIsNotNone(decoy)

    def test_get_handler_configs_no_canary(self):
        all_confs = list()
        for _ in range(10):
            all_confs.append(HandlerConf(model_type=ModelTypes.MODEL))
        all_confs.append(HandlerConf(model_type=ModelTypes.DECOY))

        handlers, canary, decoy = self.manager.get_handler_configs(all_confs)
        self.assertEqual(10, len(handlers))
        self.assertIsNone(canary)
        self.assertIsNotNone(decoy)

    def test_get_handler_configs_no_decoy(self):
        all_confs = list()
        for _ in range(10):
            all_confs.append(HandlerConf(model_type=ModelTypes.MODEL))
        all_confs.append(HandlerConf(model_type=ModelTypes.CANARY))

        handlers, canary, decoy = self.manager.get_handler_configs(all_confs)
        self.assertEqual(10, len(handlers))
        self.assertIsNotNone(canary)
        self.assertIsNone(decoy)

    def test_get_handler_configs_no_decoy_no_canary(self):
        all_confs = list()
        for _ in range(10):
            all_confs.append(HandlerConf(model_type=ModelTypes.MODEL))

        handlers, canary, decoy = self.manager.get_handler_configs(all_confs)
        self.assertEqual(10, len(handlers))
        self.assertIsNone(canary)
        self.assertIsNone(decoy)

    def test_get_handler_configs_only_decoy_and_canary(self):
        all_confs = list()
        all_confs.append(HandlerConf(model_type=ModelTypes.CANARY))
        all_confs.append(HandlerConf(model_type=ModelTypes.DECOY))

        handlers, canary, decoy = self.manager.get_handler_configs(all_confs)
        self.assertEqual(0, len(handlers))
        self.assertIsNotNone(canary)
        self.assertIsNotNone(decoy)
