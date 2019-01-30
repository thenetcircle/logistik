from typing import List
from unittest import TestCase

from logistik.cache import ICache
from logistik.config import ModelTypes
from logistik.db import HandlerConf, EventConf
from test.base import MockEnv
from logistik.discover.manager import DiscoveryService
from logistik.consul.mock import MockConsulService


class MockDb(object):
    def __init__(self):
        self.handlers = dict()

    def get_all_handlers(self) -> list:
        return list(self.handlers.values())

    def register_handler(self, handler_conf):
        self.handlers[handler_conf.node_id()] = handler_conf
        return handler_conf

    def find_one_handler(self, service_id, hostname, node):
        for model_type in [ModelTypes.MODEL, ModelTypes.CANARY]:
            node_id = HandlerConf.to_node_id(service_id, hostname, model_type, node)
            handler = self.handlers.get(node_id, None)
            if handler is not None:
                return handler
        return None

    def find_one_similar_handler(self, query_service_id):
        for node_id, handler_conf in self.handlers.items():
            service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)
            if service_id == query_service_id:
                return handler_conf
        return None


class MockCache(ICache):
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        pass

    def reset_enabled_handlers_for(self, event_name: str) -> None:
        pass

    def set_enabled_handlers_for(self, event_name: str, handlers: List[HandlerConf]):
        pass

    def get_event_conf_for(self, event_name: str) -> EventConf:
        pass

    def set_event_conf_for(self, event_name: str, conf: EventConf):
        pass


class TestDiscoveryManager(TestCase):
    def setUp(self):
        self.db = MockDb()
        self.cache = MockCache()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        self.service = DiscoveryService(self.env)

    def test_discover_none(self):
        self.service.poll_services()

    def test_discover_new(self):
        self.consul.services = {'testthing': {
            'ServiceAddress': 'localhost',
            'ServicePort': '9999',
            'ServiceTags': [
                'logistik=logistik',
                'node=0',
                'hostname=pc207'
            ],
            'ServiceName': 'testthing'
        }}
        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('9999', service.port)
        self.assertEqual('pc207', service.hostname)
        self.assertEqual('testthing', service.name)

    def test_update_one(self):
        self.consul.services = {'testthing': {
            'ServiceAddress': 'localhost',
            'ServicePort': '8888',
            'ServiceTags': [
                'logistik=logistik',
                'node=0',
                'hostname=pc207'
            ],
            'ServiceName': 'testthing'
        }}
        handler_conf = HandlerConf()
        handler_conf.service_id = 'testthing'
        handler_conf.node = '0'
        handler_conf.port = '9999'
        handler_conf.event = 'event-test'
        handler_conf.hostname = 'pc207'
        handler_conf.enabled = False
        handler_conf.name = 'testthing'
        handler_conf.model_type = ModelTypes.MODEL
        self.db.register_handler(handler_conf)

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('9999', service.port)
        self.assertEqual('pc207', service.hostname)
        self.assertEqual('testthing', service.name)
        self.assertEqual(False, service.enabled)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('8888', service.port)
        self.assertEqual('pc207', service.hostname)
        self.assertEqual('testthing', service.name)
        self.assertEqual(True, service.enabled)
