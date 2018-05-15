class AggregatedHandlerStats(object):
    def __init__(
            self, event: str=None, service_id: str=None, stat_type: str=None,
            model_type: str=None, count: int=None, node: int=None, hostname: str=None):
        self.event = event
        self.service_id = service_id
        self.stat_type = stat_type
        self.count = count
        self.model_type = model_type
        self.hostname = hostname
        self.node = node

    def to_json(self) -> dict:
        return {
            'event': self.event,
            'service_id': self.service_id,
            'stat_type': self.stat_type,
            'hostname': self.hostname,
            'model_type': self.model_type,
            'node': self.node,
            'count': self.count
        }
