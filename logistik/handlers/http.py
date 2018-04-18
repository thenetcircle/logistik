import logging

import requests
from typing import Union
from requests.models import Response
from activitystreams import Activity

from logistik import environ
from logistik.config import ConfigKeys
from logistik.config import HandlerKeys
from logistik.config import ErrorCodes
from logistik.handlers.base import BaseHandler


class HttpHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.env: environ.GNEnvironment = None
        self.method: str = None
        self.json_header = {'Context-Type': 'application/json'}

    def __str__(self):
        return HttpHandler.__class__.__name__

    def setup(self, env: environ.GNEnvironment) -> None:
        self.env = env
        try:
            http_conf = environ.env.config.get(HandlerKeys.HTTP, domain=ConfigKeys.EVENT_HANDLERS)
            self.endpoint = http_conf.get(HandlerKeys.URL)
            self.method = http_conf.get(HandlerKeys.METHOD, default='POST')
            self.timeout = http_conf.get(HandlerKeys.TIMEOUT)
            self.n_retries = http_conf.get(HandlerKeys.RETRIES)
            self.name = http_conf.get(HandlerKeys.NAME, default=HandlerKeys.HTTP)
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
