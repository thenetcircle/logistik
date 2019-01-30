from unittest import TestCase

from logistik.config import ModelTypes
from logistik.db import HandlerConf
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
        node_id = HandlerConf.to_node_id(service_id, hostname, ModelTypes.MODEL, node)
        return self.handlers.get(node_id, None)

    def find_one_similar_handler(self, query_service_id):
        for node_id, handler_conf in self.handlers.items():
            service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)
            if service_id == query_service_id:
                return handler_conf
        return None


class TestDiscoveryManager(TestCase):
    def setUp(self):
        self.db = MockDb()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul)
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
