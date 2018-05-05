from logistik.environ import env
from logistik.db.repr.handler import HandlerConf


class HandlerConfEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    service_id = env.dbman.Column(env.dbman.String(80), unique=True, nullable=False)
    name = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    event = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    enabled = env.dbman.Column(env.dbman.Boolean(), unique=False, nullable=False)
    endpoint = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    version = env.dbman.Column(env.dbman.String(16), unique=False, nullable=False, server_default='v1')
    path = env.dbman.Column(env.dbman.String(80), unique=False, nullable=True)
    node = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='0')
    method = env.dbman.Column(env.dbman.String(10), unique=False, nullable=True)
    retries = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='1')
    timeout = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='0')
    tags = env.dbman.Column(env.dbman.String(128), unique=False, nullable=True)

    def to_repr(self) -> HandlerConf:
        return HandlerConf(
            identity=self.id,
            name=self.name,
            service_id=self.service_id,
            enabled=self.enabled,
            endpoint=self.endpoint,
            version=self.version,
            path=self.path,
            node=self.node,
            method=self.method,
            retries=self.retries,
            timeout=self.timeout,
            tags=self.tags
        )

    def __str__(self):
        repr_string = """
        <HandlerConfEntity 
                id={}, name={}, event={}, enabled={}, endpoint={}, 
                version={}, path={}, method={}, retries={}, timeout={}, service_id={}, tags={}>
        """
        return repr_string.format(
            self.id, self.name, self.event, self.enabled, self.endpoint, self.version, self.path,
            self.method, self.retries, self.timeout, self.service_id, self.tags
        )
