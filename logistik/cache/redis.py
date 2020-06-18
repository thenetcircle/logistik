import logging
import sys
import ast

from typing import Optional

from logistik.config import RedisKeys
from ttldict import TTLOrderedDict

from logistik.cache import ICache
from logistik.db.reprs.handler import HandlerConf
from logistik.environ import GNEnvironment

ONE_HOUR = 60 * 60


class CacheRedis(ICache):
    def __init__(self, env: GNEnvironment, host: str, port: int = None, db: int = None):
        self.env = env
        self.ttl_dict = TTLOrderedDict(default_ttl=60 * 5)  # five minutes
        self.logger = logging.getLogger(__name__)

        if host == "mock":
            from fakeredis import FakeRedis

            self.redis = FakeRedis()
        else:
            from redis import Redis

            self.redis = Redis(host=host, port=port, db=db)

    def get_response_for(self, handler: HandlerConf, request: dict) -> Optional[dict]:
        try:
            key = self.get_response_key_from_request(handler, request)
            self.logger.info(f"checking cached value for key {key}")
            response = self.redis.get(key)

            if response is None:
                self.logger.info(f"response is None for key {key}")
                return None

            response = str(response, "utf-8")
            self.logger.info(f"response is: {response}")
            return ast.literal_eval(response)

        except Exception as e:
            self.logger.error(f"could not get response from redis: {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

            return None

    def set_response_for(self, handler: HandlerConf, request: dict, response: dict) -> None:
        try:
            # if rest api returns [response, error_code]
            if type(response) == list:
                response = response[0]

            key = self.get_response_key_from_request(handler, request)
            self.redis.set(key, str(response))
            self.redis.expire(key, 2 * ONE_HOUR)
        except Exception as e:
            self.logger.error(f"could not set response from redis: {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def _hash_for(self, handler_conf: HandlerConf):
        return handler_conf.node_id()

    def get_response_key_from_request(self, handler: HandlerConf, request: dict):
        handler_hash = self._hash_for(handler)
        provider_id = request.get("provider", dict()).get("id", "-1")
        user_id = request.get("actor", dict()).get("id", "-1")
        image_id = request.get("object", dict()).get("id", "-1")

        return RedisKeys.response_for(
            provider_id=provider_id,
            user_id=user_id,
            image_id=image_id,
            handler_hash=handler_hash
        )
