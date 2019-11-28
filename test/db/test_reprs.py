import unittest
from datetime import timedelta

from logistik.db import IDatabase, HandlerConf


class ReprTest(unittest.TestCase):
    def test_build_group_id(self):
        conf = HandlerConf(service_id='foo-bar-baz', group_id='group_id')
        self.assertEqual(conf.group_id, conf.build_group_id())

    def test_build_group_id_from_service_id(self):
        conf = HandlerConf(service_id='foo-bar-baz', group_id=None)
        self.assertEqual('foo', conf.build_group_id())

    def test_build_group_id_from_service_id_blank(self):
        conf = HandlerConf(service_id='foo-bar-baz', group_id='')
        self.assertEqual('foo', conf.build_group_id())

    def test_from_node_id_missing_one(self):
        with self.assertRaises(AttributeError):
            HandlerConf.from_node_id('service_id-hostname-model')

    def test_from_node_id(self):
        service_id, hostname, model, node = HandlerConf.from_node_id('service_id-hostname-model-0')
        self.assertEqual(service_id, 'service_id')
        self.assertEqual(hostname, 'hostname')
        self.assertEqual(model, 'model')
        self.assertEqual(node, '0')

    def test_to_json_startup(self):
        from datetime import datetime as dt
        recently = dt.utcnow() - timedelta(seconds=30)
        expected = recently.strftime('%Y-%m-%dT%H:%M:%SZ')
        conf = HandlerConf(service_id='service_id', startup=recently)

        self.assertEqual(expected, conf.to_json()['startup'])
        self.assertAlmostEqual(30, conf.to_json()['uptime'], delta=2)
