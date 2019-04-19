from logistik.environ import env
from logistik.db.reprs.handler import HandlerConf
from logistik.db.reprs.handler import HandlerStats
from logistik.config import ModelTypes

from sqlalchemy import UniqueConstraint


class HandlerStatsEntity(env.dbman.Model):
    __tablename__ = 'handler_stats_entity'

    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    service_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    name = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    event = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    endpoint = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    hostname = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    version = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    stat_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    event_time = env.dbman.Column(env.dbman.DateTime(), unique=False, nullable=False)
    event_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    event_verb = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    model_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    node = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False)

    def to_repr(self) -> HandlerStats:
        return HandlerStats(
            identity=self.id,
            name=self.name,
            service_id=self.service_id,
            hostname=self.hostname,
            endpoint=self.endpoint,
            version=self.version,
            event=self.event,
            event_time=self.event_time,
            event_id=self.event_id,
            stat_type=self.stat_type,
            event_verb=self.event_verb,
            node=self.node,
            model_type=self.model_type
        )


class HandlerConfEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    service_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    name = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    event = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    enabled = env.dbman.Column(env.dbman.Boolean(), unique=False, nullable=False, server_default='false')
    retired = env.dbman.Column(env.dbman.Boolean(), unique=False, nullable=False, server_default='false')
    endpoint = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    hostname = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    port = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False)
    version = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default='')
    path = env.dbman.Column(env.dbman.String(128), unique=False, nullable=True)
    node = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='0')
    method = env.dbman.Column(env.dbman.String(128), unique=False, nullable=True)
    model_type = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default=ModelTypes.MODEL)
    retries = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='1')
    timeout = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='0')
    tags = env.dbman.Column(env.dbman.String(256), unique=False, nullable=True)
    return_to = env.dbman.Column(env.dbman.String(128), unique=False, nullable=True)
    event_display_name = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default='event')
    startup = env.dbman.Column(env.dbman.DateTime(), unique=False, nullable=True)
    traffic = env.dbman.Column(env.dbman.Float(), unique=False, nullable=False, server_default='0.1')
    reader_type = env.dbman.Column(env.dbman.String(), unique=False, nullable=False, server_default='kafka')
    reader_endpoint = env.dbman.Column(env.dbman.String(), unique=False, nullable=True)
    consul_service_id = env.dbman.Column(env.dbman.String(), unique=False, nullable=True)

    UniqueConstraint('service_id', 'hostname', 'node', 'model_type', name='uix_1')

    def to_repr(self) -> HandlerConf:
        return HandlerConf(
            identity=self.id,
            name=self.name,
            service_id=self.service_id,
            enabled=self.enabled,
            retired=self.retired,
            event=self.event,
            endpoint=self.endpoint,
            hostname=self.hostname,
            port=self.port,
            version=self.version,
            path=self.path,
            node=self.node,
            method=self.method,
            retries=self.retries,
            model_type=self.model_type,
            timeout=self.timeout,
            tags=self.tags,
            event_display_name=self.event_display_name,
            return_to=self.return_to,
            startup=self.startup,
            traffic=self.traffic,
            reader_type=self.reader_type,
            reader_endpoint=self.reader_endpoint,
            consul_service_id=self.consul_service_id
        )

    def update(self, handler_conf: HandlerConf):
        self.name = handler_conf.name or self.name
        self.event = handler_conf.event or self.event
        self.enabled = handler_conf.enabled or self.enabled
        self.retired = handler_conf.retired or self.retired
        self.endpoint = handler_conf.endpoint or self.endpoint
        self.hostname = handler_conf.hostname or self.hostname
        self.port = handler_conf.port or self.port
        self.version = handler_conf.version or self.version
        self.path = handler_conf.path or self.path
        self.model_type = handler_conf.model_type or self.model_type
        self.node = handler_conf.node or self.node
        self.method = handler_conf.method or self.method
        self.timeout = handler_conf.timeout or self.timeout
        self.retries = handler_conf.retries or self.retries
        self.service_id = handler_conf.service_id or self.service_id
        self.return_to = handler_conf.return_to or self.return_to
        self.tags = handler_conf.tags or self.tags
        self.event_display_name = handler_conf.event_display_name or self.event_display_name
        self.startup = handler_conf.startup or self.startup
        self.traffic = handler_conf.traffic or self.traffic
        self.reader_type = handler_conf.reader_type or self.reader_type
        self.reader_endpoint = handler_conf.reader_endpoint or self.reader_endpoint
        self.consul_service_id = handler_conf.consul_service_id or self.consul_service_id

    def __str__(self):
        repr_string = """
        <HandlerConfEntity 
                id={}, name={}, event={}, enabled={}, endpoint={}, 
                version={}, path={}, method={}, retries={}, timeout={}, 
                service_id={}, tags={}, return_to={}, port={}, hostname={}. 
                startup={}, traffic={}, retired={}, reader_type={}, 
                reader_endpoint={}, event_display_name={}, consul_service_id={}>
        """
        return repr_string.format(
            self.id, self.name, self.event, self.enabled, self.endpoint, self.version, self.path,
            self.method, self.retries, self.timeout, self.service_id, self.tags, self.return_to,
            self.port, self.hostname, self.startup, self.traffic, self.retired, self.reader_type,
            self.reader_endpoint, self.event_display_name, self.consul_service_id
        )
