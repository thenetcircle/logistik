import logging
import sys

from requests import Response

from logistik.db.repr.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.queue import IKafkaWriter


class KafkaWriter(IKafkaWriter):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)

    def publish(self, conf: HandlerConf, message: Response) -> None:
        try:
            if conf.return_to is None or len(conf.return_to.strip()) == 0:
                self.logger.warning('no return-to topic specified for conf: {}'.format(conf))
                self.env.dropped_response_log.info(message.content)
        except Exception as e:
            self.logger.error('could not publish response: {}'.format(str(e)))
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            self.env.dropped_response_log.info(message.content)
