import logging

from typing import List
from typing import Union

from logistik.db import IDatabase
from logistik.environ import GNEnvironment
from logistik.db.models.handler import HandlerConfEntity
from logistik.db.models.event import EventConfEntity
from logistik.db.repr.handler import HandlerConf
from logistik.db.repr.event import EventConf

logger = logging.getLogger(__name__)


class DatabaseManager(IDatabase):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def register_handler(self, host, port, service_id, name, tags):
        handler = HandlerConfEntity.query.filter_by(service_id=service_id).first()
        if handler is not None:
            logger.debug('service with id {} already exists')
            return

        handler = HandlerConfEntity()
        handler.service_id = service_id
        handler.name = name
        handler.path = host
        handler.port = port
        handler.tags = ','.join(tags)
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        handlers = HandlerConfEntity.query\
                .filter_by(event=event_name)\
                .filter_by(enabled=True)\
                .all()

        if handlers is None or len(handlers) == 0:
            logger.warning('no handler enabled for event {}'.format(event_name))
            return list()

        handler_reprs = list()
        for handler in handlers:
            handler_reprs.append(handler.to_repr())
        return handlers

    def get_event_conf_for(self, event_name: str) -> Union[EventConf, None]:
        event = EventConfEntity.query\
                .filter_by(event=event_name)\
                .filter_by(enabled=True)\
                .first()

        if event is None:
            logger.warning('no enabled event configuration for event {}'.format(event_name))
            return None

        return event.to_repr()
