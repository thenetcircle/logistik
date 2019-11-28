from logistik.config import ConfigKeys, ModelTypes
from logistik.db import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from logistik.enrich.manager import EnrichmentManager
from logistik.queue.kafka_writer import IKafkaWriterFactory, KafkaWriter
from test.base import BaseTest
from test.base import MockEnv
from test.base import MockWriter
from test.base import MockStats

from test.discover.test_manager import MockDb, MockCache


class ResponseObject:
    def __init__(self, msg):
        self.content = msg

    def json(self):
        return self.content


class MockKafkaMessage(object):
    def __init__(self, msg):
        self.value = msg
        self.topic = 'test-topic'
        self.partition = 0
        self.offset = 1
        self.key = None


class InvalidKafkaMessage(object):
    def __init__(self, msg):
        self.value = msg


class MockProducer:
    def __init__(self, **kwargs):
        self.sent = dict()

    def send(self, topic, data):
        if topic not in self.sent:
            self.sent[topic] = list()
        self.sent[topic].append(data)


class MockKafkaWriterFactory(IKafkaWriterFactory):
    def create_producer(self, **kwargs):
        return MockProducer(**kwargs)


class KafkaWriterTest(BaseTest):
    def setUp(self):
        self.db = MockDb()
        self.failed = 0
        self.cache = MockCache()
        self.consul = MockConsulService()
        self.env = MockEnv(db=self.db, consul=self.consul, cache=self.cache)
        self.env.kafka_writer = MockWriter()
        self.env.stats = MockStats()
        self.env.enrichment_manager = EnrichmentManager(self.env)
        self.env.config.set(ConfigKeys.HOSTS, 'localhost', domain=ConfigKeys.KAFKA)

        self.writer = KafkaWriter(self.env)
        self.writer.writer_factory = MockKafkaWriterFactory()

    def test_create_producer(self):
        self.assertIsNone(self.writer.producer)
        self.writer.setup()
        self.assertIsNotNone(self.writer.producer)

    def test_try_to_publish(self):
        self.writer.setup()

        self.assertEqual(0, len(self.writer.producer.sent))
        self.writer.try_to_publish(self._gen_conf(), {'verb': 'test'})
        self.assertEqual(1, len(self.writer.producer.sent))

    def test_publish(self):
        self.writer.setup()

        self.assertEqual(0, len(self.writer.producer.sent))
        self.writer.publish(self._gen_conf(), ResponseObject({'verb': 'test'}))
        self.assertEqual(1, len(self.writer.producer.sent))

    def test_publish_json_method_fails(self):
        class DropLog:
            def __init__(self):
                self.dropped = 0

            def info(self, *args, **kwargs):
                self.dropped += 1

        dropped_log = DropLog()
        self.writer.dropped_response_log = dropped_log
        self.writer.setup()

        def fail_json():
            raise ValueError()

        message = ResponseObject({'verb': 'test'})
        message.json = fail_json

        self.assertEqual(0, dropped_log.dropped)
        self.writer.publish(self._gen_conf(), message)
        self.assertEqual(1, dropped_log.dropped)

    def test_publish_removed_retries_in_dict(self):
        self.writer.setup()

        self.assertEqual(0, len(self.writer.producer.sent))
        self.writer.publish(self._gen_conf(), ResponseObject({'verb': 'test', 'retries': 2}))
        self.assertNotIn('retries', list(self.writer.producer.sent.values())[0])

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
        handler_conf.return_to = 'return-topic'
        handler_conf.path = 'test'
        handler_conf.name = 'testthing'
        handler_conf.model_type = ModelTypes.MODEL
        return handler_conf
