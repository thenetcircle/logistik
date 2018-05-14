class HandlerStats(object):
    def __init__(self, identity=None, name=None, event=None, event_time=None,
                 endpoint=None, version=None, event_id=None, event_verb=None,
                 service_id=None, node=None, model_type=None, stat_type=None):
        self.identity = identity
        self.service_id = service_id
        self.name = name
        self.event = event
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
                 service_id=None, tags=None, return_to=None):
        self.identity: int = identity
        self.name: str = name
        self.event: str = event
        self.enabled: bool = enabled
        self.endpoint: str = endpoint
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

    def node_id(self):
        return '{}-{}-{}'.format(
            self.service_id,
            self.model_type,
            self.node
        )

    def __str__(self):
        repr_string = """
        <HandlerConf 
            identity={}, name={}, event={}, enabled={},
            endpoint={}, version={}, path={}, model_type={}, 
            node={}, method={}, timeout={}, retries={}, 
            service_id={}, tags={}, return_to={}>
        """

        return repr_string.format(
            self.identity, self.name, self.event, self.enabled, self.endpoint,
            self.version, self.path, self.model_type, self.node, self.method,
            self.timeout, self.retries, self.service_id, self.tags, self.return_to
        )

    def to_json(self):
        return {
            'identity': self.identity,
            'name': self.name,
            'event': self.event,
            'enabled': self.enabled,
            'endpoint': self.endpoint,
            'version': self.version,
            'path': self.path,
            'model_type': self.model_type,
            'node': self.node,
            'method': self.method,
            'timeout': self.timeout,
            'retries': self.retries,
            'service_id': self.service_id,
            'tags': self.tags,
            'return_to': self.return_to
        }
