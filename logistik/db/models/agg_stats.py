import datetime

from logistik.environ import env
from logistik.db.repr.agg_stats import AggregatedHandlerStats
from sqlalchemy import PrimaryKeyConstraint


class AggregatedHandlerStatsEntity(env.dbman.Model):
    """
    # having issues with generating primary key for this in sqlalchemy...
    from logistik.env.dbman.models.handler import HandlerStatsEntity
    from logistik.env.dbman.models.handler import HandlerConfEntity
    from logistik.utils.materialized_view_factory import create_mat_view

    __table__ = create_mat_view(
        'handler_stats_mv',
        env.dbman.select(
            [HandlerStatsEntity.id.label('id'),
             HandlerStatsEntity.event.label('event'),
             HandlerStatsEntity.service_id.label('service_id'),
             HandlerStatsEntity.stat_type.label('stat_type'),
             env.dbman.func.count(HandlerStatsEntity.id).label('count')]
        ).group_by(
            HandlerStatsEntity.id,
            HandlerStatsEntity.event,
            HandlerStatsEntity.service_id,
            HandlerStatsEntity.stat_type
        ))

    created manually for now:

        create view handler_stats_mv (
            event, service_id, hostname, stat_type, node, model_type, count
        ) as
        select
            event, service_id, hostname, stat_type, node, model_type, count(id) as count
        from
            handler_stats_entity
        group by
            event, service_id, hostname, stat_type, node, model_type;

    """

    __tablename__ = 'agg_handler_stats_entity'
    __table_args__ = (
        PrimaryKeyConstraint('service_id', 'event', 'hostname', 'stat_type', 'model_type', 'node'),
    )

    service_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    event = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    stat_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    hostname = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    count = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False)
    model_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    node = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False)
    timestamp = env.dbman.Column(env.dbman.DateTime(), unique=False, nullable=False, default=datetime.datetime.utcnow)

    def to_repr(self) -> AggregatedHandlerStats:
        return AggregatedHandlerStats(
            event=self.event,
            service_id=self.service_id,
            stat_type=self.stat_type,
            hostname=self.hostname,
            count=self.count,
            model_type=self.model_type,
            node=self.node
        )
