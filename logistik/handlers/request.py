import logging
import requests

from logistik.handlers import IRequester

logger = logging.getLogger(__name__)


class Requester(IRequester):
    """
    for mocking purposes
    """

    @staticmethod
    def request(method, url, json=None, headers=None, model=None, timeout=10, verbose=True):
        provider = "unknown provider"
        image_id = "unknown image_id"

        if timeout is None or int(float(timeout)) <= 0:
            timeout = 10

        if model is None:
            model = "unknown model"

        if json is not None:
            provider = json.get("provider", dict()).get("id", provider)
            image_id = json.get("object", dict()).get("id", image_id)

        try:
            response = requests.request(
                method=method, url=url, json=json, headers=headers, timeout=timeout
            )

            if verbose:
                response_code = response.status_code
                logger.info(f"[{provider}] [{image_id}]: {response_code} - {url} ({model})")

        except Exception as e:
            response_code = str(e)
            logger.info(f"[{provider}] [{image_id}]: {response_code} - {url} ({model})")
            raise e

        return response
