import requests

from logistik.handlers import IRequester


class Requester(IRequester):
    """
    for mocking purposes
    """

    @staticmethod
    def request(method, url, json=None, headers=None, timeout=10):
        return requests.request(
            method=method, url=url, json=json, headers=headers, timeout=timeout
        )
