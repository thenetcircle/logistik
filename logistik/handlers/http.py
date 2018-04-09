import logging
import sys

import requests
from typing import Union
from requests.models import Response
from activitystreams import Activity

from logistik import environ
from logistik import utils
from logistik.config import ConfigKeys
from logistik.config import HandlerKeys
from logistik.config import ErrorCodes
from logistik.handlers.base import BaseHandler

logger = logging.getLogger(__name__)
logging.getLogger()


class HttpHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.env: environ.GNEnvironment = None
        self.url: str = None
        self.method: str = None
        self.json_header = {'Context-Type': 'application/json'}
        self.timeout: int = None
        self.n_retries: int = None

    def __str__(self):
        return HttpHandler.__class__.__name__

    def setup(self, env: environ.GNEnvironment) -> None:
        self.env = env
        try:
            http_conf = environ.env.config.get(HandlerKeys.HTTP, domain=ConfigKeys.EVENT_HANDLERS)
            self.url = http_conf.get(HandlerKeys.URL)
            self.method = http_conf.get(HandlerKeys.METHOD, default='POST')
            self.json_header = {'Context-Type': 'application/json'}
            self.timeout = http_conf.get(HandlerKeys.TIMEOUT)
            self.n_retries = http_conf.get(HandlerKeys.RETRIES)
            self.name = http_conf.get(HandlerKeys.NAME, default=HandlerKeys.HTTP)
        except Exception:
            logger.info('no config enabled for {}, not enabling plugin'.format(self.__class__.__name__))
            return
        self.enabled = True

    def handle(self, data: dict, activity: Activity) -> (ErrorCodes, Union[None, Response]):
        for i in range(self.n_retries):
            try:
                return ErrorCodes.OK, requests.request(
                    method=self.method, url=self.url,
                    json=data, headers=self.json_header
                )
            except Exception as e:
                logger.error('attempt {}/{} failed for url {}, error was: {}'.format(
                    str(i+1), self.n_retries, self.url, str(e))
                )
                logger.exception(e)
                utils.fail_message(data)
                environ.env.capture_exception(sys.exc_info())
        return ErrorCodes.RETRIES_EXCEEDED, None
