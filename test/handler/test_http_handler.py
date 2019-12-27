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

        self.assertEqual(response[1].status_code, ErrorCodes.OK)
        self.assertEqual(response[0], ErrorCodes.OK)

    def test_handle_not_found(self):
        self.handler.requester = MockRequester(MockResponse(status_code=404))

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        response = self.handler.handle(data, act)

        self.assertEqual(response[1].status_code, ErrorCodes.NOT_FOUND)
        self.assertEqual(response[0], ErrorCodes.OK)

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

    def test_handle_canary_skips(self):
        self.conf.model_type = ModelTypes.CANARY
        self.conf.traffic = 0
        all_ok, _ = self.handler.handle(None, None)
        self.assertTrue(all_ok)

    def test_handle_check_canary_is_model(self):
        self.conf.model_type = ModelTypes.MODEL
        self.assertFalse(self.handler.is_canary_and_should_skip())

    def test_handle_check_canary_is_decoy(self):
        self.conf.model_type = ModelTypes.DECOY
        self.assertFalse(self.handler.is_canary_and_should_skip())

    def test_handle_check_canary_is_canary_full_traffic(self):
        self.conf.model_type = ModelTypes.CANARY
        self.conf.traffic = 1
        self.assertFalse(self.handler.is_canary_and_should_skip())

    def test_handle_check_canary_is_canary_no_traffic(self):
        self.conf.model_type = ModelTypes.CANARY
        self.conf.traffic = 0
        self.assertTrue(self.handler.is_canary_and_should_skip())

    def test_handle_empty_response(self):
        def empty_response(*args):
            return 200, ErrorCodes.OK, None

        self.handler.handle_and_return_response = empty_response

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        error_code, _ = self.handler.handle(data, act)

        self.assertEqual(error_code, ErrorCodes.HANDLER_ERROR)

    def test_handle_and_return_response_disabled_handler(self):
        self.handler.enabled = False

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        all_ok, error_code, _ = self.handler.handle_and_return_response(data, act)

        self.assertFalse(all_ok)
        self.assertEqual(error_code, ErrorCodes.HANDLER_DISABLED)

    def test_handle_and_return_response_try_to_handle_fails(self):
        self.handler.try_to_handle = None

        data = {'verb': 'test'}
        act = activitystreams.parse(data)
        all_ok, error_code, _ = self.handler.handle_and_return_response(data, act)

        self.assertFalse(all_ok)
        self.assertEqual(error_code, ErrorCodes.HANDLER_ERROR)

    def test_name_set(self):
        self.assertEqual(self.handler.name, self.conf.name)

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
