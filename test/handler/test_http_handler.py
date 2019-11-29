import sys
import types
from test.base import MockResponse


def request(method, url, json, headers):
    return MockResponse(status_code=200)


class models:
    Response = None


module_name = 'requests'
bogus_module = types.ModuleType(module_name)
sys.modules[module_name] = bogus_module
bogus_module.request = request
bogus_module.Response = MockResponse
bogus_module.models = models

from unittest import TestCase
import activitystreams

from logistik.config import ModelTypes, ErrorCodes
from logistik.db import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from test.base import MockEnv, MockStats, MockWriter, MockRequester
from test.base import MockDb, MockCache


class HttpHandlerTest(TestCase):
    def setUp(self) -> None:
        self.db = MockDb()
        self.cache = MockCache()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        self.env.kafka_writer = MockWriter()
        self.env.stats = MockStats()

        self.conf = self._gen_conf()

        from logistik.handlers.http import HttpHandler
        self.handler = HttpHandler.create(env=self.env, conf=self.conf)

        self.mock_requester = MockRequester(MockResponse(status_code=200))
        self.handler.requester = self.mock_requester

    def test_handle_200(self):
        self.handler.requester = MockRequester(MockResponse(status_code=200))

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        response = self.handler.handle(data, act)

        self.assertEqual(response[1].status_code, 200)
        self.assertEqual(response[0], ErrorCodes.OK)

    def test_handle_not_found(self):
        self.handler.requester = MockRequester(MockResponse(status_code=404))

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        response = self.handler.handle(data, act)

        self.assertEqual(response[1].status_code, ErrorCodes.NOT_FOUND.value)
        self.assertEqual(response[0], ErrorCodes.HANDLER_ERROR)

    def test_handle_unknown(self):
        self.handler.requester = MockRequester(MockResponse(status_code=123))

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        response = self.handler.handle(data, act)

        self.assertEqual(response[1].status_code, 123)
        self.assertEqual(response[0], ErrorCodes.HANDLER_ERROR)

    def test_unknown_reader_type(self):
        from logistik.handlers.http import HttpHandler
        conf = self._gen_conf()

        conf.reader_type = 'unknown'
        with self.assertRaises(ValueError):
            HttpHandler.create(env=self.env, conf=conf)

        conf.reader_type = 'kafka'
        HttpHandler.create(env=self.env, conf=conf)

    def test_handle_retries_exceeded(self):
        self.handler.requester = MockRequester(MockResponse(status_code=400))

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        response = self.handler.handle(data, act)

        self.assertEqual(response[0], ErrorCodes.RETRIES_EXCEEDED)

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
