from logistik.stats import IStats
from logistik.config import ConfigKeys


class MockStatsD(IStats):
    def __init__(self):
        self.vals = dict()
        self.timings = dict()

    def incr(self, key: str) -> None:
        if key not in self.vals:
            self.vals[key] = 1
        else:
            self.vals[key] += 1

    def decr(self, key: str) -> None:
        if key not in self.vals:
            self.vals[key] = -1
        else:
            self.vals[key] -= 1

    def timing(self, key: str, ms: int):
        self.timings[key] = ms

    def gauge(self, key: str, value: int):
        self.vals[key] = value

    def set(self, key: str, value: int):
        self.vals[key] = value


class StatsDService(IStats):
    def __init__(self, env):
        self.env = env

        conf = env.config.get(ConfigKeys.STATS_SERVICE)
        host = conf.get(ConfigKeys.HOST)

        if env.config.get(ConfigKeys.TESTING, False) or host == "mock":
            self.statsd = MockStatsD()
        else:
            import statsd
            import socket

            port = conf.get(ConfigKeys.PORT)
            prefix = "logistik"
            if ConfigKeys.PREFIX in conf:
                prefix = conf.get(ConfigKeys.PREFIX)

            prefix = "%s.%s" % (prefix, socket.gethostname())
            self.statsd = statsd.StatsClient(host, int(port), prefix=prefix)

    def incr(self, key: str) -> None:
        self.statsd.incr(key)

    def decr(self, key: str) -> None:
        self.statsd.decr(key)

    def timing(self, key: str, ms: float):
        self.statsd.timing(key, ms)

    def gauge(self, key: str, value: int):
        self.statsd.gauge(key, value)

    def set(self, key: str, value: int):
        self.statsd.set(key, value)
