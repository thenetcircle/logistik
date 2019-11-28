from activitystreams import Activity
from flask import Flask
from flask_testing import TestCase
from requests import Response

from logistik.cache.redis import CacheRedis
from logistik.config import ErrorCodes
from logistik.db import HandlerConf
from logistik.enrich.identity import IdentityEnrichment
from logistik.enrich.manager import EnrichmentManager
from logistik.enrich.published import PublishedEnrichment
from logistik.environ import ConfigDict
from logistik.environ import GNEnvironment
from logistik.handlers import IRequester
from logistik.handlers.base import BaseHandler
from logistik.queue import IKafkaWriter
from logistik.stats import IStats


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


class MockRequester(IRequester):
    def __init__(self, response):
        self.response = response

    def request(self, method, url, json, headers):
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


class MockEnv(GNEnvironment):
    def __init__(self, db=None, consul=None, cache=None):
        super().__init__(None, ConfigDict(dict()))
        self.dropped_msg_log = MockLogger()
        self.failed_msg_log = MockLogger()
        self.stats = MockStats()
        self.cache = cache
        self.db = db
        self.consul = consul
        self.event_handler_map = dict()
        self.handlers_manager = MockHandlersManager(self)
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
