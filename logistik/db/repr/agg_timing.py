class AggTiming(object):
    def __init__(
            self,
            timestamp: str = None,
            service_id: str = None,
            hostname: str = None,
            version: str = None,
            model_type: str = None,
            average: float = None,
            stddev: float = None,
            min_value: float = None,
            max_value: float = None,
            count: int = None
    ):
        self.timestamp = timestamp
        self.service_id = service_id
        self.hostname = hostname
        self.version = version
        self.model_type = model_type
        self.average = average
        self.stddev = stddev
        self.min_value = min_value
        self.max_value = max_value
        self.count = count

    def to_json(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'service_id': self.service_id,
            'hostname': self.hostname,
            'version': self.version,
            'model_type': self.model_type,
            'average': self.average,
            'stddev': self.stddev,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'count': self.count
        }
