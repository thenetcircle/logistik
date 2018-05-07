import logging
from typing import List
from typing import Union

from logistik.db import IDatabase
from logistik.db.models.event import EventConfEntity
from logistik.db.models.handler import HandlerConfEntity
from logistik.db.repr.event import EventConf
from logistik.db.repr.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.utils.decorators import with_session

logger = logging.getLogger(__name__)


class DatabaseManager(IDatabase):
    def __init__(self, env: GNEnvironment):
        self.env = env

    @with_session
    def get_all_handlers(self) -> List[HandlerConf]:
        handlers = HandlerConfEntity.query.all()
        handler_reprs = list()
        for handler in handlers:
            handler_reprs.append(handler.to_repr())
        return handler_reprs

    @with_session
    def disable_handler(self, service_id):
        handler = HandlerConfEntity.query.filter_by(service_id=service_id).first()
        if handler is None:
            logger.debug('handler with id "{}" does not exist'.format(service_id))
            return

        logger.info('disabling handler with id "{}"'.format(service_id))
        handler.enabled = False
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        if handler.event != 'UNMAPPED':
            self.env.cache.reset_enabled_handlers_for(handler.event)

    @with_session
    def register_handler(self, host, port, service_id, name, tags):
        handler = HandlerConfEntity.query.filter_by(service_id=service_id).first()
        if handler is not None:
            if handler.enabled:
                return
            logger.info('enabling handler with id "{}"'.format(service_id))
            handler.enabled = True
            self.env.dbman.session.add(handler)
            self.env.dbman.session.commit()

            if handler.event != 'UNMAPPED':
                self.env.cache.reset_enabled_handlers_for(handler.event)
            return

        logger.info('registering handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))

        handler = HandlerConfEntity()
        handler.service_id = service_id
        handler.name = name
        handler.endpoint = host
        handler.port = port
        handler.event = 'UNMAPPED'
        handler.enabled = False
        handler.tags = ','.join(tags)
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

    @with_session
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

    @with_session
    def get_event_conf_for(self, event_name: str) -> Union[EventConf, None]:
        event = EventConfEntity.query\
                .filter_by(event=event_name)\
                .filter_by(enabled=True)\
                .first()

        if event is None:
            logger.warning('no enabled event configuration for event {}'.format(event_name))
            return None

        return event.to_repr()
