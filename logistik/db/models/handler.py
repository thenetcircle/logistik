from logistik.environ import env
from logistik.db.reprs.handler import HandlerConf
from logistik.config import ModelTypes

from sqlalchemy import UniqueConstraint


class HandlerConfEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    service_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)
    group_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=True)
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
    failed_topic = env.dbman.Column(env.dbman.String(128), unique=False, nullable=True)
    event_display_name = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False, server_default='event')
    startup = env.dbman.Column(env.dbman.DateTime(), unique=False, nullable=True)
    traffic = env.dbman.Column(env.dbman.Float(), unique=False, nullable=False, server_default='0.1')
    reader_type = env.dbman.Column(env.dbman.String(), unique=False, nullable=False, server_default='kafka')
    reader_endpoint = env.dbman.Column(env.dbman.String(), unique=False, nullable=True)
    consul_service_id = env.dbman.Column(env.dbman.String(), unique=False, nullable=True)
    environment = env.dbman.Column(env.dbman.String(), unique=False, nullable=True)

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
            group_id=self.group_id,
            timeout=self.timeout,
            tags=self.tags,
            event_display_name=self.event_display_name,
            return_to=self.return_to,
            failed_topic=self.failed_topic,
            startup=self.startup,
            traffic=self.traffic,
            reader_type=self.reader_type,
            reader_endpoint=self.reader_endpoint,
            consul_service_id=self.consul_service_id,
            environment=self.environment,
        )

    def update(self, handler_conf: HandlerConf):
        self.name = handler_conf.name or self.name
        self.event = handler_conf.event or self.event

        if handler_conf.enabled is not None:
            self.enabled = handler_conf.enabled
        if handler_conf.retired is not None:
            self.retired = handler_conf.retired
        if handler_conf.node is not None:
            self.node = handler_conf.node
        if handler_conf.timeout is not None:
            self.timeout = handler_conf.timeout
        if handler_conf.retries is not None:
            self.retries = handler_conf.retries
        if handler_conf.traffic is not None:
            self.traffic = handler_conf.traffic

        self.endpoint = handler_conf.endpoint or self.endpoint
        self.hostname = handler_conf.hostname or self.hostname
        self.port = handler_conf.port or self.port
        self.version = handler_conf.version or self.version
        self.path = handler_conf.path or self.path
        self.model_type = handler_conf.model_type or self.model_type
        self.method = handler_conf.method or self.method
        self.failed_topic = handler_conf.failed_topic or self.failed_topic
        self.service_id = handler_conf.service_id or self.service_id
        self.group_id = handler_conf.group_id or self.group_id
        self.return_to = handler_conf.return_to or self.return_to
        self.tags = handler_conf.tags or self.tags
        self.event_display_name = handler_conf.event_display_name or self.event_display_name
        self.startup = handler_conf.startup or self.startup
        self.reader_type = handler_conf.reader_type or self.reader_type
        self.reader_endpoint = handler_conf.reader_endpoint or self.reader_endpoint
        self.consul_service_id = handler_conf.consul_service_id or self.consul_service_id
        self.environment = handler_conf.environment or self.environment

    def __str__(self):
        repr_string = """
        <HandlerConfEntity 
                id={}, name={}, event={}, enabled={}, endpoint={}, 
                version={}, path={}, method={}, retries={}, timeout={}, 
                service_id={}, tags={}, return_to={}, port={}, hostname={}. 
                startup={}, traffic={}, retired={}, reader_type={}, reader_endpoint={}, 
                event_display_name={}, consul_service_id={}, group_id={}, failed_topic={}
                node={}, model_type={}, environment={}>
        """
        return repr_string.format(
            self.id, self.name, self.event, self.enabled, self.endpoint, self.version, self.path,
            self.method, self.retries, self.timeout, self.service_id, self.tags, self.return_to,
            self.port, self.hostname, self.startup, self.traffic, self.retired, self.reader_type,
            self.reader_endpoint, self.event_display_name, self.consul_service_id, self.group_id,
            self.failed_topic, self.node, self.model_type, self.environment
        )
