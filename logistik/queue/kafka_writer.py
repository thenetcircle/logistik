import logging
import sys
import json

from requests import Response
from kafka import KafkaProducer

from logistik.db.reprs.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.queue import IKafkaWriter
from logistik.config import ConfigKeys

logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)


class KafkaWriter(IKafkaWriter):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.dropped_response_log = None
        self.create_loggers()

        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        self.producer = KafkaProducer(
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            bootstrap_servers=bootstrap_servers
        )

    def create_loggers(self):
        def _create_logger(_path: str, _name: str) -> logging.Logger:
            msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
            msg_handler = logging.FileHandler(_path)
            msg_handler.setFormatter(msg_formatter)
            msg_logger = logging.getLogger(_name)
            msg_logger.setLevel(logging.INFO)
            msg_logger.addHandler(msg_handler)
            return msg_logger

        d_response_path = self.env.config.get(
            ConfigKeys.DROPPED_RESPONSE_LOG, default='/tmp/logistik-dropped-responses.log')

        self.dropped_response_log = _create_logger(d_response_path, 'DroppedResponses')

    def log(self, topic: str, data: dict) -> None:
        self.producer.send(topic, data)

    def publish(self, conf: HandlerConf, message: Response) -> None:
        str_msg = None
        try:
            str_msg = message.json()
        except Exception as e:
            self.logger.error('could not decode response: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.drop_msg(message.content)

        try:
            if conf.return_to is None or len(conf.return_to.strip()) == 0:
                return

            self.try_to_publish(conf, str_msg)
        except Exception as e:
            self.logger.error('could not publish response: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.drop_msg(str_msg)

    def drop_msg(self, message):
        try:
            self.dropped_response_log.info(message)
        except Exception as e:
            self.logger.error('could not log dropped message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def try_to_publish(self, conf: HandlerConf, message) -> None:
        self.producer.send(conf.return_to, message)
