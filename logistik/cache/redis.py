import logging
import sys
from typing import List
from typing import Union

from ttldict import TTLOrderedDict

from logistik.cache import ICache
from logistik.db.reprs.handler import HandlerConf
from logistik.environ import GNEnvironment


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
