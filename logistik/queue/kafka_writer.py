import logging
import sys
import json
from abc import ABC, abstractmethod

from requests import Response

from logistik.db.reprs.handler import HandlerConf
from logistik.queue import IKafkaWriter
from logistik.config import ConfigKeys

logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)


class IKafkaWriterFactory(ABC):
    @abstractmethod
    def create_producer(self, *args, **kwargs):
        """pass"""


class KafkaWriterFactory(IKafkaWriterFactory):
    """
    for mocking purposes
    """
    def create_producer(self, **kwargs):
        from kafka import KafkaProducer
        return KafkaProducer(**kwargs)


class KafkaWriter(IKafkaWriter):
    def __init__(self, env):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.failed_msg_log = None
        self.dropped_msg_log = None
        self.dropped_response_log = None
        self.create_loggers()
        self.writer_factory = KafkaWriterFactory()
        self.producer = None

    def setup(self):
        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        self.producer = self.writer_factory.create_producer(
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            bootstrap_servers=bootstrap_servers
        )

    def publish(self, conf: HandlerConf, message: Response) -> None:
        try:
            str_msg = message.json()
        except Exception as e:
            self.logger.error('could not decode response: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.drop_msg(message.content)
            return

        self.logger.info(f"response json: {str_msg}")

        try:
            if type(str_msg) == list:
                str_msg = str_msg[0]
        except Exception as e:
            self.logger.warning(f"could not get response from list: {str(e)}")
            self.logger.warning(f"response was: {str_msg}")

        try:
            if conf.return_to is None or len(conf.return_to.strip()) == 0:
                return

            if 'retries' in str_msg:
                del str_msg['retries']

            self.try_to_publish(conf, str_msg)
        except Exception as e:
            self.logger.error('could not publish response: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.drop_msg(str_msg)

    def try_to_publish(self, conf: HandlerConf, message) -> None:
        self.producer.send(conf.return_to, message)

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

    def fail(self, topic: str, data: dict) -> None:
        if topic is None or len(topic.strip()) == 0:
            self.logger.warning(f'no failed topic configured, dropping message: {data}')
            return

        if 'retries' in data.keys():
            if data['retries'] >= 3:
                self.logger.warning(f'event has failed 3 times in a row, dropping message: {data}')
                return

            data['retries'] += 1
        else:
            data['retries'] = 1

        try:
            self.producer.send(topic, data)
        except Exception as e:
            self.logger.error(f'could not send failed event to topic {topic} because: {str(e)}')
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.drop_msg(data)

    def drop_msg(self, message):
        try:
            self.dropped_response_log.info(message)
        except Exception as e:
            self.logger.error('could not log dropped message: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
