import logging
import sys
import ast
from typing import List
from typing import Union

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

    def get_response_for(self, handler_hash, data):
        try:
            key = self._get_response_key_from_data(handler_hash, data)

            response = self.redis.get(key)

            if response is None:
                return None

            response = str(response, "utf-8")
            return ast.literal_eval(response)

        except Exception as e:
            self.logger.error("could not get response from redis: {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

            return None

    def set_response_for(self, handler_hash: str, data: dict) -> None:
        try:
            key = self._get_response_key_from_data(handler_hash, data)
            self.redis.set(key, str(data))
            self.redis.expire(key, 2 * ONE_HOUR)
        except Exception as e:
            self.logger.error("could not set response from redis: {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def _get_response_key_from_data(self, handler_hash: str, data: dict):
        provider_id = data.get("provider", dict()).get("id", "-1")
        user_id = data.get("actor", dict()).get("id", "-1")
        image_id = data.get("object", dict()).get("id", "-1")

        return RedisKeys.response_for(
            provider_id=provider_id,
            user_id=user_id,
            image_id=image_id,
            handler_hash=handler_hash
        )
