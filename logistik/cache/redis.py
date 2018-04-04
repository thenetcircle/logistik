from recs.cache import CacheBase
from recs.environ import GNEnvironment


class CacheRedis(CacheBase):
    def __init__(self, env: GNEnvironment, host: str, port: int=None, db: int=None):
        self.env = env

        if host == 'mock':
            from fakeredis import FakeRedis
            self.redis = FakeRedis()
        else:
            from redis import Redis
            self.redis = Redis(host=host, port=port, db=db)
