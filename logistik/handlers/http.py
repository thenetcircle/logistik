import logging

import requests
from typing import Union
from requests.models import Response
from activitystreams import Activity

from logistik import environ
from logistik.config import ErrorCodes
from logistik.handlers.base import BaseHandler
from logistik.db.repr.handler import HandlerConf


class HttpHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.env: environ.GNEnvironment = None
        self.method: str = None
        self.json_header = {'Context-Type': 'application/json'}

    def __str__(self):
        return HttpHandler.__class__.__name__

    def configure(self, conf: HandlerConf):
        self.enabled = conf.enabled
        self.endpoint = conf.endpoint
        self.name = conf.name
        self.version = conf.version
        self.path = conf.path
        self.method = conf.method
        self.timeout = conf.timeout
        self.n_retries = conf.retries
        self.url = '{}/{}{}'.format(self.endpoint, self.version, self.path)
        self.logger.debug('configured {} with {}'.format(str(self), str(conf)))

    def setup(self, env: environ.GNEnvironment) -> None:
        self.env = env
        try:
            self.logger = logging.getLogger(__name__)
        except Exception:
            self.logger.info('no config enabled for {}, not enabling plugin'.format(self.__class__.__name__))
            return
        self.enabled = True

    def handle_once(self, data: dict, _: Activity) -> (ErrorCodes, Union[None, Response]):
        return ErrorCodes.OK, requests.request(
            method=self.method, url=self.url,
            json=data, headers=self.json_header
        )
