class EventConf(object):
    def __init__(self, identity: int=None, name: str=None, event: str = None, enabled: bool=None, instances: int=None):
        self.identity: int = identity
        self.name: str = name
        self.event: str = event
        self.enabled: bool = enabled
        self.instances: int = instances

    def __str__(self):
        return '<EventConf identity={}, name={}, event={}, enabled={}, instances={}>'.format(
            self.identity, self.name, self.event, self.enabled, self.instances
        )
