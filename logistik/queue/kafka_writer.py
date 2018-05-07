from requests import Response

from logistik.db.repr.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.queue import IKafkaWriter


class KafkaWriter(IKafkaWriter):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def publish(self, conf: HandlerConf, message: Response) -> None:
        pass
