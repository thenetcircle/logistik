from unittest import TestCase
from test.base import MockEnv
from logistik.discover.manager import DiscoveryService
from logistik.consul.mock import MockConsulService


class MockDb(object):
    def __init__(self):
        self.handlers = dict()

    def get_all_handlers(self) -> list:
        return list(self.handlers.values())

    def register_handler(self, host, port, s_id, name, node, hostname, tags):
        return dict()


class TestDiscoveryManager(TestCase):
    def setUp(self):
        self.db = MockDb()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul)
        self.service = DiscoveryService(self.env)

    def test_discover_none(self):
        self.service.poll_services()

    def test_discover_new(self):
        self.consul.services = {'test': {
            'ServiceAddress': 'localhost',
            'ServicePort': '9999',
            'ServiceTags': [
                'logistik=logistik',
                'node=0',
                'hostname=pc207'
            ],
            'ServiceName': 'name'
        }}
        self.service.poll_services()
