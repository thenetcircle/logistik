from logistik.environ import env
from logistik.config import ModelTypes


class TimingEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)

    timestamp = env.dbman.Column(env.dbman.DateTime(), nullable=False)
    timing = env.dbman.Column(env.dbman.Float(), nullable=False)
    node = env.dbman.Column(env.dbman.Integer(), nullable=False)
    service_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    node_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    hostname = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    version = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default='')
    model_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default=ModelTypes.MODEL)
