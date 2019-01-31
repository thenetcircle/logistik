from typing import List
from unittest import TestCase

from logistik.cache import ICache
from logistik.config import ModelTypes
from logistik.db import HandlerConf, EventConf
from test.base import MockEnv
from logistik.discover.manager import DiscoveryService
from logistik.discover.consul.mock import MockConsulService


class MockDb(object):
    def __init__(self):
        self.handlers = dict()

    def get_all_handlers(self) -> list:
        return list(self.handlers.values())

    def register_handler(self, handler_conf):
        self.handlers[handler_conf.node_id()] = handler_conf
        return handler_conf

    def disable_handler(self, node_id):
        if node_id not in self.handlers:
            return
        self.handlers[node_id].enabled = False

    def enable_handler(self, node_id):
        if node_id not in self.handlers:
            return
        self.handlers[node_id].enabled = True

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
        self.consul.services = self._gen_consul_conf(hostname='machine_a')
        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('8888', service.port)
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual('testthing', service.name)

    def test_update_one(self):
        self.consul.services = self._gen_consul_conf(hostname='machine_a')
        self.db.register_handler(self._gen_conf(hostname='machine_a'))

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('9999', service.port)
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual('testthing', service.name)
        self.assertEqual(False, service.enabled)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('8888', service.port)
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual('testthing', service.name)
        self.assertEqual(True, service.enabled)

    def test_change_host_creates_new(self):
        self.consul.services = self._gen_consul_conf(hostname='machine_a')
        self.db.register_handler(self._gen_conf(hostname='machine_b'))

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('machine_b', service.hostname)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(2, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('machine_a', service.hostname)
        service = registered_services.pop()
        self.assertEqual('machine_b', service.hostname)

    def test_remove_from_consul_disables_old_handler(self):
        self.db.register_handler(self._gen_conf(enabled=True))

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual(True, service.enabled)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        service = registered_services.pop()
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual(False, service.enabled)

    def _gen_conf(self, enabled=False, hostname='machine_a'):
        handler_conf = HandlerConf()
        handler_conf.service_id = 'testthing'
        handler_conf.node = '0'
        handler_conf.port = '9999'
        handler_conf.event = 'event-test'
        handler_conf.hostname = hostname
        handler_conf.enabled = enabled
        handler_conf.name = 'testthing'
        handler_conf.model_type = ModelTypes.MODEL
        return handler_conf

    def _gen_consul_conf(self, hostname='machine_a'):
        return {'testthing': {
            'ServiceAddress': 'machine_b',
            'ServicePort': '8888',
            'ServiceTags': [
                'logistik',
                'node=0',
                'hostname={}'.format(hostname)
            ],
            'ServiceName': 'testthing'
        }}
