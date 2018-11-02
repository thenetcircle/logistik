import datetime


class HandlerStats(object):
    def __init__(self, identity=None, name=None, event=None, event_time=None,
                 endpoint=None, version=None, event_id=None, event_verb=None,
                 service_id=None, hostname=None, node=None, model_type=None, stat_type=None):
        self.identity = identity
        self.service_id = service_id
        self.name = name
        self.event = event
        self.hostname = hostname
        self.endpoint = endpoint
        self.version = version
        self.event_time = event_time
        self.event_id = event_id
        self.event_verb = event_verb
        self.node = node
        self.stat_type = stat_type
        self.model_type = model_type

    def to_json(self):
        return {
            'identity': self.identity,
            'name': self.name,
            'event': self.event,
            'hostname': self.hostname,
            'endpoint': self.endpoint,
            'version': self.version,
            'model_type': self.model_type,
            'node': self.node,
            'stat_type': self.stat_type,
            'service_id': self.service_id,
            'event_time': self.event_time,
            'event_id': self.event_id,
            'event_verb': self.event_verb
        }


class HandlerConf(object):
    def __init__(self, identity=None, name=None, event=None, enabled=None,
                 endpoint=None, version=None, path=None, model_type=None,
                 node=None, method=None, timeout=None, retries=None,
                 service_id=None, tags=None, return_to=None, port=None,
                 hostname=None, startup=None, traffic=None, retired=None,
                 reader_type=None, reader_endpoint=None):
        self.identity: int = identity
        self.name: str = name
        self.event: str = event
        self.enabled: bool = enabled
        self.retired: bool = retired
        self.endpoint: str = endpoint
        self.hostname: str = hostname
        self.port: int = port
        self.version: str = version
        self.path: str = path
        self.model_type: str = model_type
        self.node: int = node
        self.method: str = method
        self.timeout: int = timeout
        self.retries: int = retries
        self.service_id: str = service_id
        self.return_to: str = return_to
        self.tags: str = tags
        self.startup: datetime.datetime = startup
        self.traffic: float = traffic
        self.reader_type: str = reader_type
        self.reader_endpoint: str = reader_endpoint

    def node_id(self):
        return '{}-{}-{}-{}'.format(
            self.service_id,
            self.hostname,
            self.model_type,
            self.node
        )

    @staticmethod
    def to_node_id(service_id, hostname, model_type, node):
        return '{}-{}-{}-{}'.format(
            service_id,
            hostname,
            model_type,
            node
        )

    @staticmethod
    def from_node_id(node_id) -> (str, str, str, str):
        parts = node_id.rsplit('-', maxsplit=3)
        parts = node_id.rsplit('-', maxsplit=3)
        if len(parts) != 4:
            raise AttributeError('invalid node id "{}": needs to have exactly 4 parts'.format(node_id))
        return parts[0], parts[1], parts[2], parts[3]

    def __str__(self):
        repr_string = """
        <HandlerConf 
            identity={}, name={}, event={}, enabled={},
            endpoint={}, version={}, path={}, model_type={}, 
            node={}, method={}, timeout={}, retries={}, 
            service_id={}, tags={}, return_to={}, port={}, 
            hostname={}, startup={}, traffic={}, retired={}, 
            reader_type={}, reader_endpoint={}>
        """

        return repr_string.format(
            self.identity, self.name, self.event, self.enabled, self.endpoint,
            self.version, self.path, self.model_type, self.node, self.method,
            self.timeout, self.retries, self.service_id, self.tags, self.return_to,
            self.port, self.hostname, self.startup, self.traffic, self.retired,
            self.reader_type, self.reader_endpoint
        )

    def to_json(self):
        the_json = {
            'identity': self.identity,
            'name': self.name,
            'event': self.event,
            'enabled': self.enabled,
            'hostname': self.hostname,
            'endpoint': self.endpoint,
            'port': self.port,
            'version': self.version,
            'path': self.path or '',
            'model_type': self.model_type,
            'node': self.node,
            'method': self.method,
            'timeout': self.timeout,
            'retries': self.retries,
            'service_id': self.service_id,
            'startup': '',
            'retired': self.retired,
            'uptime': '0',
            'node_id': self.node_id(),
            'tags': self.tags,
            'reader_type': self.reader_type,
            'reader_endpoint': self.reader_endpoint,
            'traffic': '%s%%' % int(self.traffic * 100),
            'return_to': self.return_to or ''
        }

        if self.startup is not None:
            the_json['startup'] = self.startup.strftime('%Y-%m-%dT%H:%M:%SZ')
            the_json['uptime'] = int((datetime.datetime.utcnow() - self.startup).total_seconds())

        return the_json
