import datetime
import logging
from typing import List
from typing import Union

from sqlalchemy import func

from logistik.db import IDatabase
from logistik.db.models.agg_stats import AggregatedHandlerStatsEntity
from logistik.db.models.event import EventConfEntity
from logistik.db.models.handler import HandlerConfEntity
from logistik.db.models.handler import HandlerStatsEntity
from logistik.db.models.timing import TimingEntity
from logistik.db.repr.agg_stats import AggregatedHandlerStats
from logistik.db.repr.event import EventConf
from logistik.db.repr.handler import HandlerConf
from logistik.config import ModelTypes
from logistik.environ import GNEnvironment
from logistik.utils.decorators import with_session
from logistik.utils.exceptions import HandlerNotFoundException

logger = logging.getLogger(__name__)


class DatabaseManager(IDatabase):
    def __init__(self, env: GNEnvironment):
        self.env = env

    @with_session
    def get_all_handlers(self) -> List[HandlerConf]:
        handlers = HandlerConfEntity.query.filter_by(retired=False).all()
        return [handler.to_repr() for handler in handlers]

    @with_session
    def retire_model(self, node_id: str) -> None:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            model_type=model_type,
            node=node
        ).first()

        if handler is None:
            logger.debug('handler with node id "{}" does not exist'.format(node_id))
            return None

        logger.info('retiring {}'.format(node_id))
        handler.retired = True
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

    @with_session
    def demote_model(self, node_id: str) -> Union[HandlerConf, None]:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            model_type=model_type,
            node=node
        ).first()

        if handler is None:
            logger.debug('handler with node id "{}" does not exist'.format(node_id))
            return None

        logger.info('demoting model to canary {}'.format(node_id))
        handler.model_type = ModelTypes.CANARY
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()
        return handler.to_repr()

    @with_session
    def promote_canary(self, node_id: str) -> Union[HandlerConf, None]:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            model_type=model_type,
            node=node
        ).first()

        if handler is None:
            logger.debug('handler with node id "{}" does not exist'.format(node_id))
            return None

        logger.info('promoting canary model {}'.format(node_id))
        handler.model_type = ModelTypes.MODEL
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()
        return handler.to_repr()

    @with_session
    def timing_per_node(self) -> dict:
        return {
            row.node_id: {
                'average': row.average,
                'stddev': row.stddev,
                'min': row.min,
                'max': row.max
            } for row in
            self.env.dbman.session.query(
                TimingEntity.node_id,
                func.avg(TimingEntity.timing).label('average'),
                func.min(TimingEntity.timing).label('min'),
                func.max(TimingEntity.timing).label('max'),
                func.stddev(TimingEntity.timing).label('stddev')
            ).group_by(TimingEntity.node_id).all()
        }

    @with_session
    def timing_per_service(self) -> dict:
        return {
            row.service_id: {
                'service_id': row.service_id,
                'average': row.average,
                'stddev': row.stddev,
                'min': row.min,
                'max': row.max
            } for row in
            self.env.dbman.session.query(
                TimingEntity.service_id,
                func.avg(TimingEntity.timing).label('average'),
                func.min(TimingEntity.timing).label('min'),
                func.max(TimingEntity.timing).label('max'),
                func.stddev(TimingEntity.timing).label('stddev')
            ).group_by(TimingEntity.service_id).all()
        }

    @with_session
    def timing_per_host_and_version(self) -> list:
        return [
            {
                'service_id': row.service_id,
                'hostname': row.hostname,
                'version': row.version,
                'model_type': row.model_type,
                'average': row.average,
                'stddev': row.stddev,
                'min': row.min,
                'max': row.max
            } for row in
            self.env.dbman.session.query(
                TimingEntity.service_id,
                TimingEntity.hostname,
                TimingEntity.model_type,
                TimingEntity.version,
                func.avg(TimingEntity.timing).label('average'),
                func.min(TimingEntity.timing).label('min'),
                func.max(TimingEntity.timing).label('max'),
                func.stddev(TimingEntity.timing).label('stddev')
            ).group_by(
                TimingEntity.service_id,
                TimingEntity.hostname,
                TimingEntity.model_type,
                TimingEntity.version
            ).all()
        ]

    @with_session
    def register_runtime(self, conf: HandlerConf, time_ms: float):
        timing = TimingEntity()
        timing.version = conf.version
        timing.service_id = conf.service_id
        timing.node_id = conf.node_id()
        timing.hostname = conf.hostname
        timing.model_type = conf.model_type
        timing.timestamp = datetime.datetime.utcnow()
        timing.node = conf.node
        timing.timing = time_ms

        self.env.dbman.session.add(timing)
        self.env.dbman.session.commit()

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
    def enable_handler(self, node_id) -> None:
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

        logger.info('enabling handler with node id "{}"'.format(node_id))
        handler.enabled = True
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        if handler.event != 'UNMAPPED':
            self.env.cache.reset_enabled_handlers_for(handler.event)

    @with_session
    def disable_handler(self, node_id) -> None:
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

    def _create_handler(self, handler: HandlerConfEntity, service_id, node, name, hostname, port, host, tags_dict: dict):
        handler.enabled = True
        handler.startup = datetime.datetime.utcnow()
        handler.name = name
        handler.service_id = service_id
        handler.version = tags_dict.get('version', None) or handler.version
        handler.path = tags_dict.get('path', None) or handler.path
        handler.event = tags_dict.get('event', handler.event) or 'UNMAPPED'
        handler.return_to = tags_dict.get('returnto', None) or handler.return_to
        handler.reader_type = tags_dict.get('readertype', handler.reader_type) or 'kafka'
        handler.reader_endpoint = tags_dict.get('readerendpoint', None) or handler.reader_endpoint
        handler.node = node
        handler.hostname = hostname
        handler.endpoint = host
        handler.port = port

        return handler

    def _update_existing_handler(
            self, handler: HandlerConfEntity, service_id, node, name, hostname, port, host, tags_dict: dict
    ):
        if handler.enabled:
            return handler.to_repr()
        handler = self._create_handler(handler, service_id, node, name, hostname, port, host, tags_dict)

        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()
        if handler.event != 'UNMAPPED':
            self.env.cache.reset_enabled_handlers_for(handler.event)

        return handler.to_repr()

    def _create_new_handler(self, service_id, node, name, hostname, port, host, tags_dict: dict):
        logger.info('registering handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))

        other_service_handler = HandlerConfEntity.query.filter_by(
            service_id=service_id
        ).first()

        handler = self._create_handler(HandlerConfEntity(), service_id, node, name, hostname, port, host, tags_dict)

        # copy known values form previous handler
        if other_service_handler is not None:
            if 'event' not in tags_dict.keys():
                handler.event = other_service_handler.event
            if 'path' not in tags_dict.keys():
                handler.path = other_service_handler.path
            if 'method' not in tags_dict.keys():
                handler.method = other_service_handler.method

        handler.model_type = ModelTypes.CANARY
        handler.enabled = False

        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        return handler.to_repr()

    @with_session
    def register_handler(self, host, port, service_id, name, node, hostname, tags) -> HandlerConf:
        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            node=node
        ).first()

        tags_dict = dict()
        for tag in tags:
            if '=' not in tag:
                continue
            k, v = tag.split('=', maxsplit=1)
            tags_dict[k] = v

        if handler is not None:
            return self._update_existing_handler(handler, service_id, node, name, hostname, port, host, tags_dict)

        return self._create_new_handler(service_id, node, name, hostname, port, host, tags_dict)

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
