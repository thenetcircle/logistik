from logistik.config import ModelTypes, ConfigKeys
from logistik.db import HandlerConf
from logistik.discover.consul.mock import MockConsulService
from logistik.enrich.manager import EnrichmentManager
from logistik.queue.kafka_reader import IKafkaReaderFactory, KafkaReader
from test.base import BaseTest, MockHandlersManager
from test.base import MockRequester
from test.base import MockResponse
from test.base import MockEnv
from test.base import MockWriter
from test.base import MockStats
from test.base import MockDb, MockCache


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


class MockConsumer:
    def __init__(self, message):
        self.message = message

    def __iter__(self):
        yield self.message


class FailConsumer:
    def __init__(self, message):
        self.message = message

    def __iter__(self):
        raise ConnectionError()


class MockKafkaFactory(IKafkaReaderFactory):
    def __init__(self, message):
        self.message = message

    def create_consumer(self, *args, **kwargs):
        return MockConsumer(message=self.message)


class KafkaFailFactory(IKafkaReaderFactory):
    def __init__(self, message):
        self.message = message

    def create_consumer(self, *args, **kwargs):
        return FailConsumer(message=self.message)


class KafkaReaderTest(BaseTest):
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
        self.conf = self._gen_conf()

        from logistik.handlers.http import HttpHandler
        self.handler = HttpHandler.create(env=self.env, conf=self.conf)

        self.mock_requester = MockRequester(MockResponse(status_code=200))
        self.handler.requester = self.mock_requester

        self.reader = KafkaReader(self.env, self.conf, self.handler)

        message = MockKafkaMessage(b'{"verb":"test"}')
        self.reader.reader_factory = MockKafkaFactory(message)

    def test_create_cosnumer(self):
        self.assertIsNone(self.reader.consumer)
        self.reader.create_consumer()
        self.assertIsNotNone(self.reader.consumer)

    def test_decode(self):
        import json
        message = MockKafkaMessage(b'{"verb": "test"}')
        json.loads(message.value.decode('ascii'))

    def test_handle_message(self):
        def fail(*args, **kwargs):
            self.failed += 1

        self.reader.fail = fail
        message = MockKafkaMessage(b'{"verb": "test"}')

        self.assertEqual(0, self.failed)
        self.reader.handle_message(message)
        self.assertEqual(0, self.failed)

    def test_handle_non_json_message(self):
        class DropLog:
            def __init__(self):
                self.dropped = 0

            def info(self, *args, **kwargs):
                self.dropped += 1

        dropped_log = DropLog()
        self.reader.dropped_msg_log = dropped_log
        message = MockKafkaMessage(b'test')

        self.assertEqual(0, dropped_log.dropped)
        self.reader.handle_message(message)
        self.assertEqual(1, dropped_log.dropped)

    def test_handle_fail(self):
        class FailLog:
            def __init__(self):
                self.failed = 0

            def info(self, *args, **kwargs):
                self.failed += 1

        failed_log = FailLog()
        self.reader.failed_msg_log = failed_log

        # make sure an exception is thrown so we fail() the call
        self.reader.try_to_parse = None

        message = MockKafkaMessage(b'{"verb":"test"}')

        self.assertEqual(0, failed_log.failed)
        self.reader.handle_message(message)
        self.assertEqual(1, failed_log.failed)

    def test_can_not_parse_message(self):
        class FailLog:
            def __init__(self):
                self.failed = 0

            def info(self, *args, **kwargs):
                self.failed += 1

        failed_log = FailLog()
        self.reader.failed_msg_log = failed_log
        message = MockKafkaMessage(b'{"asdf":"test"}')

        self.assertEqual(0, failed_log.failed)
        self.reader.handle_message(message)
        self.assertEqual(1, failed_log.failed)

    def test_retries_exceeded(self):
        mock_requester = MockRequester(MockResponse(status_code=400))
        self.handler.requester = mock_requester
        self.env.handlers_manager = MockHandlersManager(self.env)

        message = MockKafkaMessage(b'{"verb": "test"}')

        self.assertEqual(0, len(self.env.handlers_manager.stopped))
        self.reader.handle_message(message)
        self.assertEqual(1, len(self.env.handlers_manager.stopped))

    def test_try_to_read(self):
        class FailLog:
            def __init__(self):
                self.failed = 0

            def info(self, *args, **kwargs):
                self.failed += 1

        failed_log = FailLog()
        self.reader.failed_msg_log = failed_log
        self.reader.create_consumer()

        self.assertEqual(0, failed_log.failed)
        self.reader.try_to_read()
        self.assertEqual(0, failed_log.failed)

    def test_run_unmapped(self):
        self.reader.conf.event = 'UNMAPPED'
        self.reader.run(sleep_time=0)
        self.assertIsNone(self.reader.consumer)

    def test_run_not_enabled(self):
        self.reader.conf.event = 'event'
        self.reader.enabled = False
        self.reader.run(sleep_time=0.1)
        self.assertIsNotNone(self.reader.consumer)

    def test_run_consume_fails(self):
        message = MockKafkaMessage(b'{"verb":"test"}')
        self.reader.reader_factory = KafkaFailFactory(message)
        self.reader.conf.event = 'event'
        self.reader.enabled = True
        self.reader.run(sleep_time=0.1, exit_on_failure=True)
        self.assertIsNotNone(self.reader.consumer)

    def test_group_id_becomes_unique_if_canary(self):
        self.reader.conf.event = 'event'
        self.reader.conf.model_type = ModelTypes.CANARY
        self.assertTrue(len(self.reader.group_id().split('-')) > 3)

    def test_group_id_not_unique_if_model(self):
        self.reader.conf.event = 'event'
        self.reader.conf.model_type = ModelTypes.MODEL
        self.assertEqual(2, len(self.reader.group_id().split('-')))

    def test_try_to_read_disabled_handler(self):
        message = MockKafkaMessage(b'{"verb":"test"}')
        self.reader.reader_factory = MockKafkaFactory(message)
        self.reader.conf.event = 'event'
        self.reader.enabled = False
        self.reader.create_consumer()
        self.reader.try_to_read()
        self.assertIsNotNone(self.reader.consumer)

    def test_try_to_read_handle_throws_exception(self):
        class FailLog:
            def __init__(self):
                self.failed = 0

            def info(self, *args, **kwargs):
                self.failed += 1

        failed_log = FailLog()
        self.reader.failed_msg_log = failed_log

        message = InvalidKafkaMessage(b'test')
        self.reader.reader_factory = MockKafkaFactory(message)
        self.reader.create_consumer()

        self.assertEqual(0, failed_log.failed)
        self.reader.try_to_read()
        self.assertEqual(1, failed_log.failed)

    def test_fail_msg_kafka_writer_fails(self):
        class FailLog:
            def __init__(self):
                self.failed = 0

            def info(self, *args, **kwargs):
                self.failed += 1

        failed_log = FailLog()
        self.reader.failed_msg_log = failed_log
        self.env.kafka_writer = None

        self.assertEqual(0, failed_log.failed)
        self.reader.fail_msg('asdf', 'some-topic', dict())
        self.assertEqual(1, failed_log.failed)

    def test_drop_msg_kafka_writer_fails(self):
        class DropLog:
            def __init__(self):
                self.dropped = 0

            def info(self, *args, **kwargs):
                self.dropped += 1

        dropped_log = DropLog()
        self.reader.dropped_msg_log = dropped_log
        self.env.kafka_writer = None

        self.assertEqual(0, dropped_log.dropped)
        self.reader.drop_msg('asdf', 'some-topic', dict())
        self.assertEqual(1, dropped_log.dropped)

    def test_parsing(self):
        verb = 'foo'
        actor_id = 'bar'
        data = {
            'verb': verb,
            'actor': {'id': actor_id}
        }
        _, activity = self.reader.try_to_parse(data)

        self.assertEqual(verb, activity.verb)
        self.assertEqual(actor_id, activity.actor.id)

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
