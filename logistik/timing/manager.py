from logistik.timing import ITimingManager
from logistik.environ import GNEnvironment


class TimingManager(ITimingManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_timing_summary(self) -> dict:
        return {
            'node': self.env.db.timing_per_node(),
            'service': self.env.db.timing_per_service(),
            'version': self.env.db.timing_per_host_and_version()
        }
