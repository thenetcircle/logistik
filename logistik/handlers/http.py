import logging
import os

import eventlet
from activitystreams import Activity

from logistik.config import ErrorCodes, HandlerType
from logistik.db.reprs.handler import HandlerConf
from logistik.handlers.base import BaseHandler
from logistik.handlers.request import Requester
from logistik.queue.kafka_reader import KafkaReader
from logistik.queue.mock_reader import MockReader
from logistik.queue.rest_reader import RestReader


class HttpHandler(BaseHandler):
    def __init__(self, handler_type: HandlerType = None):
        super().__init__()
        self.env = None
        self.handler_type: HandlerType = handler_type
        self.requester = Requester()
        self.method: str = None
        self.json_header = {'Context-Type': 'application/json'}
        self.schema = 'http://'
        self.logger = logging.getLogger(__name__)

        log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
        if log_level == 'DEBUG':
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        self.logger.setLevel(log_level)
        self.enabled = False
        self.name = ''

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
            self.method = 'POST'

        separator = ''
        if self.path is not None and self.path[0] != '/':
            separator = '/'

        self.url = '{}{}:{}/{}{}'.format(
            self.schema,
            self.endpoint,
            self.port,
            separator,
            self.path
        )
        self.logger.debug('configured {} for url {}'.format(str(self), self.url))

    def setup(self, env) -> None:
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.logger.info(self.conf)

        if self.conf.reader_type == 'kafka':
            self.reader = KafkaReader(env, self.conf, self, self.handler_type)
            self.reader_thread = eventlet.spawn(self.reader.run)
        elif self.conf.reader_type == 'rest':
            self.reader = RestReader(env, self.conf, self)
            self.reader_thread = eventlet.spawn_after(func=self.reader.run, seconds=1)
        elif self.conf.reader_type == 'mock':
            self.reader = MockReader(env, self.conf, self)
            self.reader_thread = eventlet.spawn_after(func=self.reader.run, seconds=1)
        else:
            raise ValueError('unknown reader type {}'.format(self.conf.reader_type))

        self.enabled = True

    def start(self):
        self.reader.start()

    def stop(self):
        self.reader.stop()

    def handle_once(self, data: dict, _: Activity, **kwargs) -> tuple:
        self.logger.debug(f'data to send: {data}')
        self.logger.debug(f'method={self.method}, url={self.url}, json=<data>, headers={self.json_header}')

        response = self.requester.request(
            method=self.method, url=self.url,
            json=data, headers=self.json_header
        )

        if response.status_code == ErrorCodes.OK.value:
            return ErrorCodes.OK, response

        elif response.status_code == ErrorCodes.NO_CONTENT.value:
            return ErrorCodes.NO_CONTENT, None

        elif response.status_code == ErrorCodes.NOT_FOUND.value:
            return ErrorCodes.NOT_FOUND, response

        else:
            return ErrorCodes.UNKNOWN_ERROR, response
