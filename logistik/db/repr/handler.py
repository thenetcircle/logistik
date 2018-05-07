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
