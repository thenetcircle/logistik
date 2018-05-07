class AggregatedHandlerStats(object):
    def __init__(self, event: str=None, service_id: str=None, stat_type: str=None, count: int=None):
        self.event = event,
        self.service_id = service_id,
        self.stat_type = stat_type,
        self.count = count

    def to_json(self) -> dict:
        return {
            'event': self.event,
            'service_id': self.service_id,
            'stat_type': self.stat_type,
            'count': self.count
        }
