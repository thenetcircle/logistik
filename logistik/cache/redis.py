from logistik.cache import ICache
from logistik.environ import GNEnvironment

from typing import List
from typing import Union
from logistik.db.repr.handler import HandlerConf
from logistik.db.repr.event import EventConf
from ttldict import TTLOrderedDict


class CacheRedis(ICache):
    def __init__(self, env: GNEnvironment, host: str, port: int=None, db: int=None):
        self.env = env
        self.ttl_dict = TTLOrderedDict(default_ttl=60*5)  # five minutes

        if host == 'mock':
            from fakeredis import FakeRedis
            self.redis = FakeRedis()
        else:
            from redis import Redis
            self.redis = Redis(host=host, port=port, db=db)

    def get_enabled_handlers_for(self, event_name: str) -> Union[None, List[HandlerConf]]:
        try:
            return self.ttl_dict.get('handlers-{}'.format(event_name))
        except KeyError:
            return None

    def set_enabled_handlers_for(self, event_name: str, handlers: List[HandlerConf]):
        self.ttl_dict['handlers-{}'.format(event_name)] = handlers

    def get_event_conf_for(self, event_name: str) -> Union[None, EventConf]:
        try:
            return self.ttl_dict.get('events-{}'.format(event_name))
        except KeyError:
            return None

    def set_event_conf_for(self, event_name: str, conf: EventConf):
        self.ttl_dict['events-{}'.format(event_name)] = conf
