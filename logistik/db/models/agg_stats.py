from logistik import environ
from logistik.db.repr.agg_stats import AggregatedHandlerStats
from sqlalchemy import PrimaryKeyConstraint

db = environ.env.dbman


class AggregatedHandlerStatsEntity(db.Model):
    """
    # having issues with generating primary key for this in sqlalchemy...
    from logistik.db.models.handler import HandlerStatsEntity
    from logistik.db.models.handler import HandlerConfEntity
    from logistik.utils.materialized_view_factory import create_mat_view

    __table__ = create_mat_view(
        'handler_stats_mv',
        db.select(
            [HandlerStatsEntity.id.label('id'),
             HandlerStatsEntity.event.label('event'),
             HandlerStatsEntity.service_id.label('service_id'),
             HandlerStatsEntity.stat_type.label('stat_type'),
             db.func.count(HandlerStatsEntity.id).label('count')]
        ).group_by(
            HandlerStatsEntity.id,
            HandlerStatsEntity.event,
            HandlerStatsEntity.service_id,
            HandlerStatsEntity.stat_type
        ))

    created manually for now:

        create materialized view handler_stats_mv (
            event, service_id, stat_type, node, model_type, count
        ) as
        select
            event, service_id, stat_type, node, model_type, count(id) as count
        from
            handler_stats_entity
        group by
            event, service_id, stat_type, node, model_type;

    """

    __tablename__ = 'handler_stats_mv'
    __table_args__ = (
        PrimaryKeyConstraint('service_id', 'event', 'stat_type', 'model_type', 'node'),
    )

    service_id = db.Column(db.String(80), unique=False, nullable=False)
    event = db.Column(db.String(80), unique=False, nullable=False)
    stat_type = db.Column(db.String(16), unique=False, nullable=False)
    count = db.Column(db.Integer(), unique=False, nullable=False)
    model_type = db.Column(db.String(16), unique=False, nullable=False)
    node = db.Column(db.Integer(), unique=False, nullable=False)

    def to_repr(self) -> AggregatedHandlerStats:
        return AggregatedHandlerStats(
            event=self.event,
            service_id=self.service_id,
            stat_type=self.stat_type,
            count=self.count,
            model_type=self.model_type,
            node=self.node
        )
