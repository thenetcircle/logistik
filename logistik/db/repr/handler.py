class HandlerConf(object):
    def __init__(self, identity=None, name=None, event=None, enabled=None,
                 endpoint=None, version=None, path=None, model_type=None, node=None):
        self.identity: int = identity
        self.name: str = name
        self.event: str = event
        self.enabled: bool = enabled
        self.endpoint: str = endpoint
        self.version: str = version
        self.path: str = path
        self.model_type: str = model_type
        self.node: int = node

    def __str__(self):
        repr_string = '<HandlerConf identity={}, name={}, event={}, enabled={}, ' \
               'endpoint={}, version={}, path={}, model_type={}, node={}>'

        return repr_string.format(
            self.identity, self.name, self.event, self.enabled, self.endpoint,
            self.version, self.path, self.model_type, self.node
        )
