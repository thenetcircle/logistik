import logging
import os

import eventlet
from activitystreams import Activity

from logistik.config import HandlerType
from logistik.db.reprs.handler import HandlerConf
from logistik.handlers.base import BaseHandler
from logistik.handlers.request import Requester
from logistik.queue.kafka_reader import KafkaReader
from logistik.queue.mock_reader import MockReader
from logistik.queue.rest_reader import RestReader

logger = logging.getLogger(__name__)


class HttpHandler(BaseHandler):
    @staticmethod
    def call_handler(data: dict, handler_conf: HandlerConf, return_dict: dict):
        schema = "http://"
        endpoint = handler_conf.endpoint
        path = handler_conf.path
        method = handler_conf.method
        timeout = handler_conf.timeout
        port = handler_conf.port
        json_header = {"Context-Type": "application/json"}

        if method is None or len(method.strip()) == 0:
            method = "POST"

        separator = ""
        if path is not None and path[0] != "/":
            separator = "/"

        url = "{}{}:{}{}{}".format(
            schema, endpoint, port, separator, path
        )

        response = Requester.request(
            method=method, url=url, json=data, headers=json_header, timeout=timeout
        )

        return response.status_code, response





    def __init__(self, handler_type: HandlerType = None):
        super().__init__()
        self.env = None
        self.handler_type: HandlerType = handler_type
        self.requester = Requester()
        self.method: str = None
        self.json_header = {"Context-Type": "application/json"}
        self.schema = "http://"
        self.logger = logging.getLogger(__name__)

        log_level = os.environ.get("LOG_LEVEL", "DEBUG")
        if log_level == "DEBUG":
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        self.logger.setLevel(log_level)
        self.enabled = False
        self.name = ""

    def __str__(self):
        return HttpHandler.__class__.__name__

    @staticmethod
    def create(env, conf: HandlerConf, handler_type: HandlerType = None):
        handler = HttpHandler(handler_type=handler_type)
        handler.configure(conf)
        handler.setup(env)
        return handler

    def configure(self, conf: HandlerConf):
        self.enabled = conf.enabled
        self.endpoint = conf.endpoint
        self.name = conf.name
        self.path = conf.path
        self.method = conf.method
        self.timeout = conf.timeout
        self.n_retries = conf.retries
        self.port = conf.port
        self.conf = conf

        if self.method is None or len(self.method.strip()) == 0:
            self.method = "POST"

        separator = ""
        if self.path is not None and self.path[0] != "/":
            separator = "/"

        self.url = "{}{}:{}{}{}".format(
            self.schema, self.endpoint, self.port, separator, self.path
        )
        self.logger.info(f"configured {str(self)} for url {self.url}")

    def setup(self, env) -> None:
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.logger.info(self.conf)

        reader_type = self.conf.reader_type

        # TODO: try to run as a separate process
        if reader_type == "kafka":
            self.reader = KafkaReader(env, self.conf, self, self.handler_type)
            self.reader_thread = eventlet.spawn(self.reader.run)
        elif reader_type == "rest":
            self.reader = RestReader(env, self.conf, self)
            self.reader_thread = eventlet.spawn_after(func=self.reader.run, seconds=1)
        elif reader_type == "mock":
            self.reader = MockReader(env, self.conf, self)
            self.reader_thread = eventlet.spawn_after(func=self.reader.run, seconds=1)
        else:
            raise ValueError(f"unknown reader type {reader_type}")

        self.enabled = True

    def start(self):
        self.reader.start()

    def stop(self):
        self.reader.stop()

    def handle_once(self, data: dict, _: Activity, **kwargs) -> tuple:
        self.logger.debug(f"data to send: {data}")
        self.logger.debug(
            f"method={self.method}, url={self.url}, json=<data>, headers={self.json_header}"
        )

        response = self.requester.request(
            method=self.method, url=self.url, json=data, headers=self.json_header
        )

        return response.status_code, response
