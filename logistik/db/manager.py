import logging
from typing import List
from typing import Union

from logistik.db import IDatabase
from logistik.db.models.event import EventConfEntity
from logistik.db.models.handler import HandlerConfEntity
from logistik.db.models.handler import HandlerStatsEntity
from logistik.db.models.agg_stats import AggregatedHandlerStatsEntity
from logistik.db.repr.event import EventConf
from logistik.db.repr.agg_stats import AggregatedHandlerStats
from logistik.db.repr.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.utils.exceptions import HandlerNotFoundException
from logistik.utils.decorators import with_session

logger = logging.getLogger(__name__)


class DatabaseManager(IDatabase):
    def __init__(self, env: GNEnvironment):
        self.env = env

    @with_session
    def get_all_handlers(self) -> List[HandlerConf]:
        handlers = HandlerConfEntity.query.all()
        return [handler.to_repr() for handler in handlers]

    @with_session
    def get_all_enabled_handlers(self):
        handlers = HandlerConfEntity.query.filter_by(enabled=True).all()
        return [handler.to_repr() for handler in handlers]

    @with_session
    def get_all_stats(self):
        stats = HandlerStatsEntity.query.all()
        return [stat.to_repr() for stat in stats]

    @with_session
    def get_all_aggregated_stats(self) -> List[AggregatedHandlerStats]:
        stats = AggregatedHandlerStatsEntity.query.all()
        return [stat.to_repr() for stat in stats]

    @with_session
    def disable_handler(self, node_id):
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            model_type=model_type,
            node=node
        ).first()

        if handler is None:
            logger.debug('handler with node id "{}" does not exist'.format(node_id))
            return

        logger.info('disabling handler with node id "{}"'.format(node_id))
        handler.enabled = False
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        if handler.event != 'UNMAPPED':
            self.env.cache.reset_enabled_handlers_for(handler.event)

    @with_session
    def get_handler_for(self, node_id: str) -> HandlerConf:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            model_type=model_type,
            node=node
        ).first()

        if handler is None:
            raise HandlerNotFoundException(node_id)
        return handler.to_repr()

    @with_session
    def register_handler(self, host, port, service_id, name, node, model_type, hostname, tags) -> HandlerConf:
        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            node=node,
            model_type=model_type
        ).first()

        version = None
        for tag in tags:
            if 'version=' in tag:
                version = tag.split('=', maxsplit=1)[1]
                break

        if handler is not None:
            if handler.enabled:
                return handler.to_repr()
            node_id = HandlerConf.to_node_id(service_id, hostname, model_type, node)
            logger.info('enabling handler with node id "{}"'.format(node_id))
            handler.enabled = True
            handler.name = name
            handler.version = version or handler.version
            handler.node = node
            handler.model_type = model_type
            handler.hostname = hostname
            handler.endpoint = host
            handler.port = port
            self.env.dbman.session.add(handler)
            self.env.dbman.session.commit()

            if handler.event != 'UNMAPPED':
                self.env.cache.reset_enabled_handlers_for(handler.event)
            return handler.to_repr()

        logger.info('registering handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))

        other_service_handler = HandlerConfEntity.query.filter_by(
            service_id=service_id
        ).first()

        handler = HandlerConfEntity()
        handler.event = 'UNMAPPED'
        handler.service_id = service_id
        handler.name = name
        handler.version = version or ''
        handler.node = node
        handler.model_type = model_type
        handler.hostname = hostname
        handler.endpoint = host
        handler.port = port
        handler.enabled = False

        if other_service_handler is not None:
            handler.event = other_service_handler.event
            handler.path = other_service_handler.path
            handler.method = other_service_handler.method

            # TODO: version should come from tags, maybe "github describe" on client side
            handler.version = other_service_handler.version

        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        return handler.to_repr()

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
