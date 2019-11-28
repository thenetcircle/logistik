import sys
import types


class MockConsul:
    class Catalog:
        def __init__(self):
            self._services = {
                'foobar': {
                    "Node": "foobar",
                    "Address": "10.1.10.12",
                    "ServiceID": "redis",
                    "ServiceName": "redis",
                    "ServiceTags": None,
                    "ServicePort": 8000
                }
            }

        def service(self, name):
            return 1, self._services.get(name, None)

        def services(self):
            return 1, list(self._services.values())

    class Agent:
        class Service:
            def deregister(self, service_id: str):
                pass

        def __init__(self):
            self.service = MockConsul.Agent.Service()

    def __init__(self, host, port):
        self.catalog = MockConsul.Catalog()
        self.agent = MockConsul.Agent()


module_name = 'consul'
bogus_module = types.ModuleType(module_name)
sys.modules[module_name] = bogus_module
bogus_module.Consul = MockConsul

from logistik.discover.consul.consul import ConsulService
from test.base import MockEnv
from test.base import BaseTest


class TestConsul(BaseTest):
    def setUp(self):
        self.env = MockEnv()
        self.consul = ConsulService(self.env)

    def test_mock_consul(self):
        print(self.consul.consul.__dict__)

    def test_get_service_none(self):
        self.assertIsNone(self.consul.get_service('foo')[1])

    def test_get_service(self):
        self.assertIsNotNone(self.consul.get_service('foobar')[1])

    def test_get_services(self):
        self.assertIsNotNone(self.consul.get_services()[1][0])

    def test_deregister(self):
        self.assertIsNone(self.consul.deregister('foobar'))
