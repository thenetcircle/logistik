import json
import sys
import logging
import traceback

from uuid import uuid4 as uuid
from kafka import KafkaConsumer
from activitystreams import parse as parse_as
from activitystreams import Activity

from logistik import utils
from logistik.config import ConfigKeys
from logistik.environ import GNEnvironment

logger = logging.getLogger(__name__)


class KafkaReader(object):
    def __init__(self, env: GNEnvironment):
        self.logger = logging.getLogger(__name__)
        self.env = env

    def run(self) -> None:
        bootstrap_servers = self.env.config.get(ConfigKeys.HOSTS, domain=ConfigKeys.KAFKA)
        self.logger.info('bootstrapping from servers: %s' % (str(bootstrap_servers)))

        topic_name = self.env.config.get(ConfigKeys.TOPIC, domain=ConfigKeys.KAFKA)
        self.logger.info('consuming from topic {}'.format(topic_name))

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
        self.logger.debug("%s:%d:%d: key=%s value=%s" % (
            message.topic, message.partition,
            message.offset, message.key,
            message.value)
        )

        try:
            data, activity = self.try_to_parse(message)
        except InterruptedError:
            self.logger.warning('got interrupt, dropping message'.format(str(message.value)))
            utils.drop_message(message.value)
            raise
        except utils.ParseException:
            self.logger.error('could not enrich/parse data, original data was: {}'.format(str(message.value)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            utils.fail_message(message.value)
            return
        except Exception as e:
            self.logger.error('got uncaught exception: {}'.format(str(e)))
            self.logger.error('event was: {}'.format(str(message)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            utils.fail_message(message.value)
            return

        try:
            self.try_to_handle(data, activity)
        except InterruptedError:
            raise
        except Exception as e:
            self.logger.error('got uncaught exception: {}'.format(str(e)))
            self.logger.error('event was: {}'.format(str(data)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            utils.fail_message(data)

    def try_to_parse(self, message) -> (dict, Activity):
        data = message.value

        try:
            enriched_data = self.env.enrichment_manager.handle(data)
        except Exception as e:
            return utils.ParseException(e)

        try:
            activity = parse_as(enriched_data)
            return data, activity
        except Exception as e:
            raise utils.ParseException(e)

    def try_to_handle(self, data: dict, activity: Activity) -> None:
        if activity.verb not in self.env.event_handler_map:
            self.logger.error('no plugin enabled for event {}, dropping message'.format(activity.verb))
            utils.drop_message(data)
            return

        self.env.handlers_manager.handle(data, activity)
