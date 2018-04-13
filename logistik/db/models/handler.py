from logistik.environ import env
from logistik.db.repr.handler import HandlerConf


class HandlerConfEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    name = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    event = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    enabled = env.dbman.Column(env.dbman.Boolean(), unique=False, nullable=False)
    endpoint = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    version = env.dbman.Column(env.dbman.String(16), unique=False, nullable=False, server_default='v1')
    path = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    node = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='0')

    def to_repr(self) -> HandlerConf:
        return HandlerConf(
            identity=self.id,
            name=self.name,
            enabled=self.enabled,
            endpoint=self.endpoint,
            version=self.version,
            path=self.path,
            node=self.node
        )

    def __str__(self):
        return '<HandlerConfEntity id={}, name={}, event={}, enabled={}, endpoint={}, version={}, path={}>'.format(
            self.id, self.name, self.event, self.enabled, self.endpoint, self.version, self.path
        )
