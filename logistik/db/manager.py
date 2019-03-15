import datetime
import logging
from typing import List
from typing import Union

from sqlalchemy import func

from logistik.db import IDatabase, AggTiming
from logistik.db.models.agg_stats import AggregatedHandlerStatsEntity
from logistik.db.models.agg_timing import AggTimingEntity
from logistik.db.models.event import EventConfEntity
from logistik.db.models.handler import HandlerConfEntity
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
    def timing_per_host_and_version(self) -> List[dict]:
        return [
            {
                'service_id': row.service_id,
                'hostname': row.hostname,
                'version': row.version,
                'model_type': row.model_type,
                'average': row.average,
                'stddev': row.stddev,
                'timestamp': row.timestamp,
                'min': row.min,
                'max': row.max,
                'count': row.count
            } for row in
            self.env.dbman.session.query(
                TimingEntity.service_id,
                TimingEntity.hostname,
                TimingEntity.model_type,
                TimingEntity.version,
                func.count(TimingEntity.id).label('count'),
                func.max(TimingEntity.timestamp).label('timestamp'),
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

    @with_session
    def find_one_handler(self, service_id, hostname, node) -> Union[HandlerConf, None]:
        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            node=node
        ).first()

        if handler is None:
            return None
        return handler.to_repr()

    @with_session
    def find_one_similar_handler(self, service_id):
        other_service_handler = HandlerConfEntity.query.filter_by(
            service_id=service_id
        ).first()

        if other_service_handler is None:
            return None
        return other_service_handler.to_repr()

    @with_session
    def register_handler(self, handler_conf: HandlerConf) -> HandlerConf:
        handler = HandlerConfEntity.query.filter_by(
            service_id=handler_conf.service_id,
            hostname=handler_conf.hostname,
            node=handler_conf.node
        ).first()

        if handler is None:
            handler = HandlerConfEntity()

        handler.update(handler_conf)

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

    @with_session
    def save_aggregated_entity(self, timing: AggTiming) -> None:
        entity = AggTimingEntity()

        entity.timestamp = timing.timestamp
        entity.service_id = timing.service_id
        entity.hostname = timing.hostname
        entity.version = timing.version
        entity.model_type = timing.model_type
        entity.average = timing.average
        entity.stddev = timing.stddev
        entity.min_value = timing.min_value
        entity.max_value = timing.max_value
        entity.count = timing.count

        self.env.dbman.session.add(entity)
        self.env.dbman.session.commit()

    @with_session
    def remove_old_timings(self, timing: AggTiming) -> None:
        TimingEntity.query.filter(
            TimingEntity.service_id == timing.service_id,
            TimingEntity.hostname == timing.hostname,
            TimingEntity.model_type == timing.model_type,
            TimingEntity.version == timing.version,
            TimingEntity.timestamp <= timing.timestamp
        ).delete()
        self.env.dbman.session.commit()
