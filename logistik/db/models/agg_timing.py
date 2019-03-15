from logistik.db.repr.agg_timing import AggTiming
from logistik.environ import env
from logistik.config import ModelTypes


class AggTimingEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)

    timestamp = env.dbman.Column(env.dbman.DateTime(), nullable=False)
    service_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    hostname = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    version = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default='')
    model_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default=ModelTypes.MODEL)
    average = env.dbman.Column(env.dbman.Float(), nullable=False)
    stddev = env.dbman.Column(env.dbman.Float(), nullable=False)
    min_value = env.dbman.Column(env.dbman.Float(), nullable=False)
    max_value = env.dbman.Column(env.dbman.Float(), nullable=False)
    count = env.dbman.Column(env.dbman.Integer(), nullable=False)

    def to_repr(self) -> AggTiming:
        return AggTiming(
            timestamp=self.timestamp,
            service_id=self.service_id,
            hostname=self.hostname,
            version=self.version,
            model_type=self.model_type,
            average=self.average,
            stddev=self.stddev,
            min_value=self.min_value,
            max_value=self.max_value,
            count=self.count
        )
