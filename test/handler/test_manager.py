from unittest import TestCase
from uuid import uuid4 as uuid

from logistik.config import ModelTypes
from logistik.db.reprs.handler import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from logistik.handlers.manager import HandlersManager
from test.base import MockEnv, MockStats, MockWriter, MockRequester, MockResponse
from test.base import MockCache, MockDb


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

    def test_query_offline(self):
        conf = HandlerConf(model_type=ModelTypes.MODEL, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')
        self.manager.add_handler(conf)

        handlers = self.manager.get_handlers()
        self.assertListEqual(list(), handlers)

    def test_query_not_implemented(self):
        self.manager.requester = MockRequester(MockResponse(status_code=404))

        conf = HandlerConf(model_type=ModelTypes.MODEL, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')
        self.manager.add_handler(conf)

        handlers = self.manager.get_handlers()
        self.assertListEqual(list(), handlers)

    def test_query_online(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=ModelTypes.MODEL, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')
        self.env.db.register_handler(conf)
        self.manager.add_handler(conf)

        handlers = self.manager.get_handlers()
        self.assertEqual(1, len(handlers))
        self.assertEqual(self.db.get_all_handlers()[0].event, 'the-event')
        self.assertEqual(self.db.get_all_handlers()[0].return_to, 'return')

    def test_add_no_model_type(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=None, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')
        self.manager.add_handler(conf)

        handlers = self.manager.get_handlers()
        self.assertEqual(0, len(handlers))

    def test_add_correct_model_type(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')
        self.manager.add_handler(conf)

        handlers = self.manager.get_handlers()
        self.assertEqual(1, len(handlers))

    def test_add_twice(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.manager.add_handler(conf)
        handlers = self.manager.get_handlers()
        self.assertEqual(1, len(handlers))

        self.manager.add_handler(conf)
        handlers = self.manager.get_handlers()
        self.assertEqual(1, len(handlers))

    def test_query_ints(self):
        response = {
            'retries': '6',
            'timeout': '37'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.env.db.register_handler(conf)
        self.manager.add_handler(conf)

        self.assertEqual(self.db.get_all_handlers()[0].retries, 6)
        self.assertEqual(self.db.get_all_handlers()[0].timeout, 37)

    def test_query_wrong_ints(self):
        response = {
            'retries': 'three',
            'timeout': 'ten'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.env.db.register_handler(conf)
        self.manager.add_handler(conf)

        self.assertEqual(self.db.get_all_handlers()[0].retries, 1)
        self.assertEqual(self.db.get_all_handlers()[0].timeout, 0)

    def test_query_invalid_field(self):
        response = {
            'event': 3
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))

        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.env.db.register_handler(conf)
        self.manager.add_handler(conf)

        self.assertNotEqual(self.db.get_all_handlers()[0].event, 3)

    def test_start_handler(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))
        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.env.db.register_handler(conf)
        self.manager.start_handler(conf.node_id())

        handlers = self.manager.get_handlers()
        self.assertEqual(1, len(handlers))

    def test_start_non_existing_handler(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))
        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.manager.start_handler(conf.node_id())

        handlers = self.manager.get_handlers()
        self.assertEqual(0, len(handlers))

    def test_stop_non_existing_handler(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))
        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.manager.stop_handler(conf.node_id())

        handlers = self.manager.get_handlers()
        self.assertEqual(0, len(handlers))

    def test_stop_existing_handler(self):
        response = {
            'return_to': 'return',
            'event': 'the-event'
        }
        self.manager.requester = MockRequester(MockResponse(status_code=200, data=response))
        conf = HandlerConf(model_type=ModelTypes.DECOY, reader_type='kafka', service_id=str(uuid()), event='UNMAPPED')

        self.env.db.register_handler(conf)
        self.manager.start_handler(conf.node_id())
        handlers = self.manager.get_handlers()
        self.assertEqual(1, len(handlers))

        self.manager.stop_handler(conf.node_id())
        handlers = self.manager.get_handlers()
        self.assertEqual(0, len(handlers))
