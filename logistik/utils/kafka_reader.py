import logging
import time
import json
import sys
import traceback

from uuid import uuid4 as uuid
from kafka import KafkaConsumer
from activitystreams import parse as parse_as

from logistik.utils import ParseException
from logistik.utils.base_store import IDataStore
from logistik.config import ConfigKeys
from logistik.environ import GNEnvironment


class KafkaReader(object):
    def __init__(self, data_store: IDataStore, env: GNEnvironment):
        self.logger = logging.getLogger(__name__)
        self.data_store = data_store
        self.env = env

    def run(self) -> None:
        while not self.data_store.init_done:
            time.sleep(1)

        topic_name = self.env.config.get(ConfigKeys.TOPIC, domain=ConfigKeys.KAFKA)
        self.logger.debug('data store initialized, starting to read from kafka, topic {}'.format(topic_name))

        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        self.logger.debug('bootstrapping from servers: %s' % (str(bootstrap_servers)))

        consumer = KafkaConsumer(
            topic_name,
            group_id='{}-{}'.format(self.env.config.get(ConfigKeys.MODEL_NAME), str(uuid())),
            value_deserializer=lambda m: json.loads(m.decode('ascii')),
            bootstrap_servers=bootstrap_servers,
            enable_auto_commit=True,
            connections_max_idle_ms=9 * 60 * 1000,
        )

        while True:
            try:
                for message in consumer:
                    self.handle_message(message)
            except InterruptedError:
                self.logger.info('got interrupted, shutting down...')
                break

    def handle_message(self, message) -> None:
        try:
            self.try_to_handle_message(message)
        except InterruptedError:
            raise
        except ParseException:
            self.logger.error('activity stream was: {}'.format(str(message.value)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
        except Exception as e:
            self.logger.error('got uncaught exception: {}'.format(str(e)))
            self.logger.error('event was: {}'.format(str(message)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())

    def try_to_handle_message(self, message) -> None:
        self.logger.debug("%s:%d:%d: key=%s value=%s" % (
            message.topic, message.partition,
            message.offset, message.key,
            message.value)
        )

        try:
            activity = parse_as(message.value)
        except Exception as e:
            self.logger.error('could not parse message as activity stream: {}'.format(str(e)))
            raise ParseException(e)

        try:
            percentages = json.loads(activity.object.content)
        except Exception as e:
            self.logger.error('could not parse content of activity stream: {}'.format(str(e)))
            raise ParseException(e)

        if not all([key in percentages for key in ['a', 'b', 'c', 'd']]):
            error_msg = 'not all required keys existed in activity.object.content: {}'.format(str(percentages))
            self.logger.error(error_msg)
            raise ParseException(error_msg)

        self.data_store.update_score(
            int(activity.actor.id),
            activity.object.id,
            (
                percentages.get('a'),
                percentages.get('b'),
                percentages.get('c'),
                percentages.get('d')
            )
        )
