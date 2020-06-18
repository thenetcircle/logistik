import logging
import requests

from logistik.handlers import IRequester

logger = logging.getLogger(__name__)


class Requester(IRequester):
    """
    for mocking purposes
    """

    @staticmethod
    def request(method, url, json=None, headers=None, timeout=10):
        provider = json.get("provider", dict()).get("id", "unknown provider")
        image_id = json.get("object", dict()).get("id", "unknown id")

        try:
            response = requests.request(
                method=method, url=url, json=json, headers=headers, timeout=timeout
            )

            response_code = response.status_code
            logger.info(f"[{provider}] [{image_id}]: {response_code} - {url}")

        except Exception as e:
            response_code = str(e)
            logger.info(f"[{provider}] [{image_id}]: {response_code} - {url}")
            raise e

        return response
