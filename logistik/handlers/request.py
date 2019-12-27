import requests

from logistik.handlers import IRequester


class Requester(IRequester):
    """
    for mocking purposes
    """

    def request(self, method, url, json=None, headers=None):
        return requests.request(method=method, url=url, json=json, headers=headers)
