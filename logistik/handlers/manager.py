import logging
import sys
import random
import traceback
from abc import ABC

from activitystreams import Activity

from logistik.db.models.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.handlers.base import BaseHandler
from logistik.config import ModelTypes
from logistik import utils

logger = logging.getLogger(__name__)


class IHandlersManager(ABC):
    def handle(self, data: dict, activity: Activity) -> None:
        """
        handle the event and possible tell the kafka writer to send a response

        :param data: the original event, before being parsed into a activity streams model
        :param activity: the incoming event in activity streams format
        :return: nothing
        """


class HandlersManager(IHandlersManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def handle(self, data: dict, activity: Activity) -> None:
        event_name = activity.verb
        handler_confs = self.env.db.get_enabled_handlers_for(event_name)
        event_conf = self.env.db.get_event_conf_for(event_name)

        if len(handler_confs) == 0:
            logger.warning('[{}] dropping event, no handler configured: {}'.format(event_name, data))
            utils.drop_message(data)
            return

        n_instances = event_conf.instances
        if n_instances > len(handler_confs) or n_instances <= 0:
            n_instances = len(handler_confs)

        handler = self.env.event_handler_map[event_name]

        self._call_handlers(handler, n_instances, handler_confs, data, activity)

    def _call_handlers(self, handler: BaseHandler, n_instances: int, all_confs: list, data: dict, activity: Activity):
        handler_confs, canary_conf, decoy_conf = self._get_handler_configs(all_confs)

        if n_instances < len(handler_confs):
            for i in range(n_instances):
                handler_conf = random.choice(handler_confs)
                handler_confs.remove(handler_conf)
                self._handle_event_with(handler, handler_conf, data, activity)
        else:
            for handler_conf in handler_confs:
                self._handle_event_with(handler, handler_conf, data, activity)

        if canary_conf is not None:
            self._handle_event_with(handler, canary_conf, data, activity)
        if decoy_conf is not None:
            self._handle_event_with(handler, decoy_conf, data, activity)

    def _get_handler_configs(self, all_confs):
        canary_conf = None
        decoy_conf = None
        handler_confs = list()

        for handler_conf in all_confs:
            if handler_conf.type == ModelTypes.CANARY:
                canary_conf = handler_conf
            elif handler_conf.type == ModelTypes.DECOY:
                decoy_conf = handler_conf
            else:
                handler_confs.append(handler_conf)

        return handler_confs, canary_conf, decoy_conf

    def _handle_event_with(self, handler: BaseHandler, conf: HandlerConf, data: dict, activity: Activity):
        try:
            handler.configure(conf)
        except Exception as e:
            logger.error('[{}] could not configure handler {} for config {}: {}'.format(
                conf.event, str(handler), str(conf), str(e)
            ))
            utils.fail_message(data)
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return

        try:
            all_ok, status_code, msg = handler(data, activity)
            if all_ok:
                logger.info('[{}] handler "{}" success'.format(conf.event, str(handler)))
            else:
                logger.error('[{}] handler "{}" failed: {}'.format(conf.event, str(handler), str(msg)))

        except Exception as e:
            logger.error('[{}] could not execute handler {} because: {}'.format(conf.event, str(handler), str(e)))
            utils.fail_message(data)
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return
