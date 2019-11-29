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
        self.consumer.get_json = lambda: {'verb': 'test'}

    def test_post(self):
        _, error_code = self.consumer.post()
        self.assertEqual(200, error_code)

    def test_post_get_json_fails(self):
        self.consumer.get_json = None
        _, error_code = self.consumer.post()
        self.assertEqual(400, error_code)

    def test_post_handle_message_fails(self):
        self.consumer.handle_message = None
        _, error_code = self.consumer.post()
        self.assertEqual(500, error_code)

    def test_handle_message(self):
        response, error_code = self.consumer.handle_message({'verb': 'test'})
        self.assertEqual(200, error_code)

    def test_handle_message_parse_fails(self):
        self.consumer.try_to_parse = None
        response, error_code = self.consumer.handle_message({'verb': 'test'})
        self.assertEqual(500, error_code)

    def test_handle_message_parsing_fails(self):
        def parse_throws_exception(_):
            raise ParseException()

        self.consumer.try_to_parse = parse_throws_exception
        response, error_code = self.consumer.handle_message({'verb': 'test'})
        self.assertEqual(400, error_code)

    def test_handle_returns_not_ok(self):
        def handle_returns_weird_value(data, _):
            return ErrorCodes.HANDLER_ERROR, data

        self.consumer.handler.handle = handle_returns_weird_value
        response, error_code = self.consumer.handle_message({'verb': 'test'})
        self.assertEqual(500, error_code)

    def test_handle_raises_exception(self):
        def handle_raises_exception(*args):
            raise RuntimeError()

        self.consumer.failed_msg_log = FailLog()
        self.consumer.handler.handle = handle_raises_exception
        self.assertEqual(0, self.consumer.failed_msg_log.failed)

        response, error_code = self.consumer.handle_message({'verb': 'test'})
        self.assertEqual(500, error_code)
        self.assertEqual(1, self.consumer.failed_msg_log.failed)

    def test_handle_raises_interrupted(self):
        def handle_raises_interrupted(*args):
            raise InterruptedError()

        self.consumer.dropped_msg_log = DropLog()
        self.consumer.handler.handle = handle_raises_interrupted
        self.assertEqual(0, self.consumer.dropped_msg_log.dropped)

        response, error_code = self.consumer.handle_message({'verb': 'test'})
        self.assertEqual(500, error_code)
        self.assertEqual(1, self.consumer.dropped_msg_log.dropped)


    def test_parse(self):
        data, act = self.consumer.try_to_parse({'verb': 'test'})

        self.assertEqual(data['verb'], 'test')
        self.assertEqual(act.verb, 'test')

    def test_fail(self):
        self.consumer.failed_msg_log = FailLog()

        self.assertEqual(0, self.consumer.failed_msg_log.failed)
        self.consumer.fail_msg('asdf')
        self.assertEqual(1, self.consumer.failed_msg_log.failed)

    def test_drop(self):
        self.consumer.dropped_msg_log = DropLog()

        self.assertEqual(0, self.consumer.dropped_msg_log.dropped)
        self.consumer.drop_msg('asdf')
        self.assertEqual(1, self.consumer.dropped_msg_log.dropped)

    def test_fail_crash(self):
        self.consumer.failed_msg_log = None

        # should not throw exception
        self.consumer.fail_msg('asdf')

    def test_create_loggers(self):
        self.consumer.create_loggers()

        self.assertIsNotNone(self.consumer.failed_msg_log)
        self.assertIsNotNone(self.consumer.dropped_msg_log)

    def test_drop_crash(self):
        self.consumer.dropped_msg_log = None

        # should not throw exception
        self.consumer.drop_msg('asdf')

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
