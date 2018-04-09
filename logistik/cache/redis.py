from logistik.cache import ICache
from logistik.environ import GNEnvironment


class CacheRedis(ICache):
    def __init__(self, env: GNEnvironment, host: str, port: int=None, db: int=None):
        self.env = env

        if host == 'mock':
            from fakeredis import FakeRedis
            self.redis = FakeRedis()
        else:
            from redis import Redis
            self.redis = Redis(host=host, port=port, db=db)
