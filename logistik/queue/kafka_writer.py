import logging
import sys
import json

from requests import Response
from kafka import KafkaProducer

from logistik.db.repr.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.queue import IKafkaWriter
from logistik.config import ConfigKeys

logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)


class KafkaWriter(IKafkaWriter):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)

        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        self.producer = KafkaProducer(
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            bootstrap_servers=bootstrap_servers
        )

    def log(self, topic: str, data: dict) -> None:
        self.producer.send(topic, data)

    def publish(self, conf: HandlerConf, message: Response) -> None:
        try:
            if conf.return_to is None or len(conf.return_to.strip()) == 0:
                self.logger.warning('no return-to topic specified for conf: {}'.format(conf))
                self.env.dropped_response_log.info(message.content)

            self.try_to_publish(conf, message)
        except Exception as e:
            self.logger.error('could not publish response: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.env.dropped_response_log.info(message.content)

    def try_to_publish(self, conf: HandlerConf, message: Response) -> None:
        self.producer.send(conf.return_to, message.content)
