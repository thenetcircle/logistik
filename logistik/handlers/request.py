import logging
import requests
import opentracing
from opentracing import Format

from logistik.handlers import IRequester

logger = logging.getLogger(__name__)


class Requester(IRequester):
    """
    for mocking purposes
    """

    @staticmethod
    def request(method, url, json=None, headers=None, model=None, timeout=10, verbose=True, child_span=None):
        provider = "unknown provider"
        image_id = "unknown image_id"
        event_id = "unknown act id"

        if timeout is None or int(float(timeout)) <= 0:
            timeout = 10

        if model is None:
            model = "unknown model"

        if json is not None:
            provider = json.get("provider", dict()).get("id", provider)
            image_id = json.get("object", dict()).get("id", image_id)
            event_id = json.get("id", event_id)[:8]

        try:
            if child_span is not None:
                headers = headers or dict()
                opentracing.global_tracer().inject(
                    span_context=child_span.context,
                    format=Format.HTTP_HEADERS,
                    carrier=headers
                )

            response = requests.request(
                method=method, url=url, json=json, headers=headers, timeout=timeout
            )

            if verbose:
                response_code = response.status_code
                logger.info(f"[{provider}] [{event_id}] [{image_id}]: {response_code} - {url} ({model})")

        except Exception as e:
            response_code = str(e)
            logger.error(f"[{provider}] [{event_id}] [{image_id}]: {response_code} - {url} ({model})")
            raise e

        return response
