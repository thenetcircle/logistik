from unittest import TestCase

from logistik.config import ModelTypes, ErrorCodes
from logistik.db import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from logistik.handlers.http import HttpHandler
from logistik.queue.mock_reader import MockConsumer, MockReader
from logistik.utils.exceptions import ParseException
from test.base import MockEnv, MockRequester, MockResponse, MockEnrichmentManager, MockKafkaWriter, FailLog, DropLog
from test.base import MockDb, MockCache


class TestMockConsumer(TestCase):
    def setUp(self) -> None:
        self.db = MockDb()
        self.cache = MockCache()
        self.consul = MockConsulService()
        self.mock_requester = MockRequester(MockResponse(status_code=200))

        self.env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        self.env.enrichment_manager = MockEnrichmentManager()
        self.env.kafka_writer = MockKafkaWriter()

        self.handler_conf = self._gen_conf()
        self.handler = HttpHandler.create(env=self.env, conf=self.handler_conf)
        self.handler.requester = self.mock_requester

        self.reader = MockReader(self.env, self.handler_conf, self.handler)
        self.consumer = MockConsumer(env=self.env, reader=self.reader, conf=self.handler_conf, handler=self.handler)

    def test_handle_message(self):
        self.assertIsNone(self.reader.url)
        self.reader.run()
        self.assertIsNotNone(self.reader.url)

    def test_register_consumer(self):
        self.assertEqual(1, len(self.reader.consumers))
        self.reader.register_consumer(self.consumer)
        self.assertEqual(2, len(self.reader.consumers))

    def test_run_unmapped(self):
        self.reader.conf.event = 'UNMAPPED'
        self.assertIsNone(self.reader.url)
        self.reader.run()
        self.assertIsNone(self.reader.url)

    def test_stop(self):
        self.assertTrue(self.reader.consumers[0].enabled)
        self.reader.stop()
        self.assertFalse(self.reader.consumers[0].enabled)

    def test_start(self):
        self.reader.stop()
        self.assertFalse(self.reader.consumers[0].enabled)
        self.reader.start()
        self.assertTrue(self.reader.consumers[0].enabled)

    def _gen_conf(self, enabled=False, hostname='machine_a'):
        handler_conf = HandlerConf()
        handler_conf.service_id = 'testthing'
        handler_conf.node = '0'
        handler_conf.port = '9999'
        handler_conf.event = 'event-test'
        handler_conf.reader_type = 'kafka'
        handler_conf.hostname = hostname
        handler_conf.enabled = enabled
        handler_conf.retries = 3
        handler_conf.timeout = 10
        handler_conf.endpoint = 'localhost'
        handler_conf.path = 'test'
        handler_conf.name = 'testthing'
        handler_conf.model_type = ModelTypes.MODEL
        return handler_conf
