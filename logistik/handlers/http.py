import logging

from logistik.handlers.base import BaseHandler
from logistik.handlers.request import Requester

logger = logging.getLogger(__name__)


class HttpHandler(BaseHandler):
    @staticmethod
    def call_handler(data: dict, handler_conf, return_dict: dict):
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

        url = "{}{}:{}{}{}".format(schema, endpoint, port, separator, path)

        response = Requester.request(
            method=method, url=url, json=data, headers=json_header, timeout=timeout
        )

        return_dict[handler_conf] = (response.status_code, response)
