import logging
import sys
from typing import List
from typing import Union

from ttldict import TTLOrderedDict

from logistik.cache import ICache
from logistik.db.reprs.handler import HandlerConf
from logistik.environ import GNEnvironment


class CacheRedis(ICache):
    def __init__(self, env: GNEnvironment, host: str, port: int=None, db: int=None):
        self.env = env
        self.ttl_dict = TTLOrderedDict(default_ttl=60*5)  # five minutes
        self.logger = logging.getLogger(__name__)

        if host == 'mock':
            from fakeredis import FakeRedis
            self.redis = FakeRedis()
        else:
            from redis import Redis
            self.redis = Redis(host=host, port=port, db=db)

    def get_enabled_handlers_for(self, event_name: str) -> Union[None, List[HandlerConf]]:
        return self.ttl_dict.get('handlers-{}'.format(event_name))

    def reset_enabled_handlers_for(self, event_name: str) -> None:
        handler_name = 'handlers-{}'.format(event_name)
        if handler_name in self.ttl_dict:
            try:
                del self.ttl_dict[handler_name]
            except KeyError as e:
                self.logger.warning('could not delete key {} from cache, might be a race condition'.format(str(e)))
                self.env.capture_exception(sys.exc_info())

    def set_enabled_handlers_for(self, event_name: str, handlers: List[HandlerConf]):
        self.ttl_dict['handlers-{}'.format(event_name)] = handlers
