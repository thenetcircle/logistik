from unittest import TestCase

from logistik.config import ModelTypes, ConfigKeys, HandlerTypes
from logistik.db import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from logistik.discover.manager import DiscoveryService
from test.base import MockEnv, MockDb, MockCache


class TestDiscoveryManager(TestCase):
    def setUp(self):
        self.db = MockDb()
        self.cache = MockCache()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        self.service = DiscoveryService(self.env)

    def test_interval_normal(self):
        interval = 5
        env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        env.config.set(ConfigKeys.INTERVAL, interval)

        self.assertEqual(DiscoveryService(env).interval, interval)

    def test_interval_too_low(self):
        interval = 0
        env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        env.config.set(ConfigKeys.INTERVAL, interval)

        self.assertEqual(DiscoveryService(env).interval, 1)

    def test_interval_too_high(self):
        interval = 5000
        env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        env.config.set(ConfigKeys.INTERVAL, interval)

        self.assertEqual(DiscoveryService(env).interval, 3600)

    def test_non_logistik_service(self):
        # like normally, with a logistik tag, should be registered
        self.consul.services = self._gen_consul_conf()
        self.service.poll_services()
        self.assertEqual(1, len(list(self.db.handlers.values())))

        # clean the services
        self.consul.services = dict()
        self.env.db.handlers.clear()
        self.service.poll_services()
        self.assertEqual(0, len(list(self.db.handlers.values())))

        # same thing but without the 'logistik' tag, should not be registered
        services = self._gen_consul_conf()
        services[list(services.keys())[0]]['ServiceTags'].remove('logistik')
        self.consul.services = services
        self.service.poll_services()
        self.assertEqual(0, len(list(self.db.handlers.values())))

    def test_no_hostname(self):
        # like normally, with a hostname, should be registered
        self.consul.services = self._gen_consul_conf()
        self.service.poll_services()
        self.assertEqual(1, len(list(self.db.handlers.values())))

        # clean the services
        self.consul.services = dict()
        self.env.db.handlers.clear()
        self.service.poll_services()
        self.assertEqual(0, len(list(self.db.handlers.values())))

        # same thing but without the hostname, should not be registered
        services = self._gen_consul_conf(hostname='foo')
        services[list(services.keys())[0]]['ServiceTags'].remove('hostname=foo')
        self.consul.services = services
        self.service.poll_services()
        self.assertEqual(0, len(list(self.db.handlers.values())))

    def test_add_twice(self):
        self.consul.services = self._gen_consul_conf()
        self.service.poll_services()
        self.assertEqual(1, len(list(self.db.handlers.values())))

        self.service.poll_services()
        self.assertEqual(1, len(list(self.db.handlers.values())))

    def test_add_poll_enabled_model(self):
        self.consul.services = self._gen_consul_conf()
        self.service.poll_services()
        self.assertEqual(1, len(list(self.db.handlers.values())))

        handlers = list(self.db.handlers.values())
        self.db.promote_canary(handlers[0][HandlerTypes.DEFAULT].node_id())
        self.db.enable_handler(handlers[0][HandlerTypes.DEFAULT].node_id())

        # poll again and make sure we only have one
        self.service.poll_services()
        self.assertEqual(1, len(list(self.db.handlers.values())))

    def test_double_tags_overwrite(self):
        hostname = 'bar'

        services = self._gen_consul_conf(hostname='machine_a')
        services[list(services.keys())[0]]['ServiceTags'].append('hostname=' + hostname)

        self.consul.services = services
        self.service.poll_services()

        handlers = list(self.db.handlers.values())
        self.assertEqual(1, len(handlers))

        self.assertEqual(hostname, handlers[0][HandlerTypes.DEFAULT].hostname)

    def test_discover_none(self):
        self.service.poll_services()

    def test_discover_new(self):
        self.consul.services = self._gen_consul_conf(hostname='machine_a')
        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('8888', service.port)
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual('testthing', service.name)

    def test_update_one(self):
        self.consul.services = self._gen_consul_conf(hostname='machine_a')
        self.db.register_handler(self._gen_conf(hostname='machine_a'))

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('9999', service.port)
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual('testthing', service.name)
        self.assertEqual(False, service.enabled)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('8888', service.port)
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual('testthing', service.name)
        self.assertEqual(True, service.enabled)

    def test_change_host_creates_new(self):
        self.consul.services = self._gen_consul_conf(hostname='machine_a')
        self.db.register_handler(self._gen_conf(hostname='machine_b'))

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('machine_b', service.hostname)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(2, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('machine_a', service.hostname)

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('machine_b', service.hostname)

    def test_remove_from_consul_disables_old_handler(self):
        self.db.register_handler(self._gen_conf(enabled=True))

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual(True, service.enabled)

        self.service.poll_services()

        registered_services = list(self.db.handlers.values())
        self.assertEqual(1, len(registered_services))

        services = registered_services.pop()
        service = services[HandlerTypes.DEFAULT]
        self.assertEqual('machine_a', service.hostname)
        self.assertEqual(False, service.enabled)

    def test_run_exists_on_interrupt(self):
        def poll_raises_interrupt():
            raise InterruptedError()

        self.service.poll_services = poll_raises_interrupt
        self.service.run()

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
