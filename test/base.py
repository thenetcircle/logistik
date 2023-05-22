from activitystreams import Activity
from flask import Flask
from flask_testing import TestCase
from requests import Response
from typing import List

from logistik.cache import ICache
from logistik.cache.redis import CacheRedis
from logistik.config import ErrorCodes, ServiceTags, ModelTypes, HandlerType
from logistik.db import HandlerConf
from logistik.enrich.identity import IdentityEnrichment
from logistik.enrich.manager import EnrichmentManager
from logistik.enrich.published import PublishedEnrichment
from logistik.environ import ConfigDict
from logistik.environ import GNEnvironment
from logistik.handlers import IRequester
from logistik.handlers.base import BaseHandler
from logistik.queues import IKafkaWriter
from logistik.queues.kafka_writer import IKafkaWriterFactory
from logistik.stats import IStats
from logistik.utils.exceptions import HandlerNotFoundException


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


class MockLogger(object):
    def __init__(self):
        self.drops = 0

    def info(self, _):
        self.drops += 1

    def warning(self, _):
        self.drops += 1


class MockHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.n_handled = 0

    def setup(self, env: GNEnvironment):
        self.enabled = True

    def handle(self, data: dict, activity: Activity):
        self.n_handled += 1
        return BaseHandler.OK, ErrorCodes.OK, dict()


class MockResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


class MockRequester(IRequester):
    def __init__(self, response: MockResponse):
        self.response = response

    def request(self, method, url, json=None, headers=None):
        if self.response.status_code == 400:
            raise ConnectionError()
        return self.response


class MockWriter(IKafkaWriter):
    def log(self, topic: str, data: dict) -> None:
        pass

    def fail(self, topic: str, data: dict) -> None:
        pass

    def drop(self, topic: str, data: dict) -> None:
        pass

    def publish(self, conf: HandlerConf, message: Response) -> None:
        pass


class MockStats(IStats):
    def incr(self, key: str) -> None:
        pass

    def decr(self, key: str) -> None:
        pass

    def timing(self, key: str, ms: float):
        pass

    def gauge(self, key: str, value: int):
        pass

    def set(self, key: str, value: int):
        pass


class MockHandlersManager(object):
    def __init__(self, env):
        self.env = env
        self.started = set()
        self.stopped = set()

    def start_handler(self, node_id):
        if node_id in self.stopped:
            self.stopped.remove(node_id)
        self.started.add(node_id)
        self.env.db.enable_handler(node_id)

    def stop_handler(self, node_id):
        if node_id in self.started:
            self.started.remove(node_id)
        self.stopped.add(node_id)
        self.env.db.disable_handler(node_id)


class MockKafkaWriter:
    def publish(self, conf, message):
        return


class MockEnrichmentManager:
    def handle(self, data):
        return data


class FailLog:
    def __init__(self):
        self.failed = 0

    def info(self, *args, **kwargs):
        self.failed += 1


class DropLog:
    def __init__(self):
        self.dropped = 0

    def info(self, *args, **kwargs):
        self.dropped += 1


class MockDb(object):
    def __init__(self):
        self.handlers = dict()
        self.env = None

    def setup(self, env):
        self.env = env

    def get_all_enabled_handlers(self):
        handlers = list()

        for handlers in self.handlers.values():
            if handlers[self.env.handler_types[0].name].enabled:
                handlers.append(handlers[self.env.handler_types[0].name])

        return handlers

    def get_all_handlers(self) -> list:
        return [handlers[self.env.handler_types[0].name] for handlers in self.handlers.values()]

    def update_handler(self, handler_conf: HandlerConf):
        if handler_conf.node_id() not in self.handlers:
            return

        fields = ['return_to', 'event', 'method', 'retries', 'timeout', 'group_id', 'path', 'failed_topic']
        for handler_type in self.env.handler_types:
            for field in fields:
                updated = handler_conf.__getattribute__(field)
                self.handlers[handler_conf.node_id()][handler_type.name].__setattr__(field, updated)


class MockCache(ICache):
    pass


class MockEnv(GNEnvironment):
    def __init__(self, db=None, consul=None, cache=None):
        super().__init__(None, ConfigDict(dict()))
        self.dropped_msg_log = MockLogger()
        self.failed_msg_log = MockLogger()
        self.stats = MockStats()
        self.cache = cache
        self.db = db

        if self.db is not None:
            self.db.setup(self)

        self.consul = consul
        self.event_handler_map = dict()
        self.handlers_manager = MockHandlersManager(self)
        self.handler_types = [
            HandlerType('default'),
            HandlerType('low_priority', 0.2, 'low')
        ]
        self.enrichment_manager = None
        self.enrichers = [
            ('published', PublishedEnrichment()),
            ('id', IdentityEnrichment()),
        ]


class BaseTest(TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    def setUp(self):
        self.env = MockEnv()
        self.env.handlers_manager = MockHandler()
        self.env.enrichment_manager = EnrichmentManager(self.env)
        self.env.cache = CacheRedis(self.env, host='mock')
