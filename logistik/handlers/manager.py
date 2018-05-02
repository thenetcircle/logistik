import logging
import random
import sys
import traceback

from typing import List
from activitystreams import Activity

from logistik import utils
from logistik.config import ModelTypes
from logistik.db.repr.handler import HandlerConf
from logistik.db.repr.event import EventConf
from logistik.environ import GNEnvironment
from logistik.handlers import IHandler
from logistik.handlers import IHandlersManager

logger = logging.getLogger(__name__)


class HandlersManager(IHandlersManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def load_event_conf(self, event_name: str) -> EventConf:
        event_conf = self.env.cache.get_event_conf_for(event_name)
        if event_conf is not None:
            return event_conf

        event_conf = self.env.db.get_event_conf_for(event_name)
        self.env.cache.set_event_conf_for(event_name, event_conf)
        return event_conf

    def load_handler_confs(self, event_name: str) -> List[HandlerConf]:
        handler_confs = self.env.cache.get_enabled_handlers_for(event_name)
        if handler_confs is not None:
            return handler_confs

        handler_confs = self.env.db.get_enabled_handlers_for(event_name)
        self.env.cache.set_enabled_handlers_for(event_name, handler_confs)
        return handler_confs

    def handle(self, data: dict, activity: Activity) -> None:
        event_name = activity.verb

        handler_confs = self.load_handler_confs(event_name)
        event_conf = self.load_event_conf(event_name)

        if len(handler_confs) == 0:
            logger.warning('[{}] dropping event, no handler configured: {}'.format(event_name, data))
            utils.drop_message(data)
            return

        n_instances = event_conf.instances
        if n_instances > len(handler_confs) or n_instances <= 0:
            n_instances = len(handler_confs)

        handler = self.env.event_handler_map[event_name]
        self.call_handlers(handler, n_instances, handler_confs, data, activity)

    def call_handlers(self, handler: IHandler, n_instances: int, all_confs: list, data: dict, activity: Activity):
        handler_confs, canary_conf, decoy_conf = self.get_handler_configs(all_confs)

        if n_instances < len(handler_confs):
            for i in range(n_instances):
                handler_conf = random.choice(handler_confs)
                handler_confs.remove(handler_conf)
                self.handle_event_with(handler, handler_conf, data, activity)
        else:
            for handler_conf in handler_confs:
                self.handle_event_with(handler, handler_conf, data, activity)

        if canary_conf is not None:
            self.handle_event_with(handler, canary_conf, data, activity)
        if decoy_conf is not None:
            self.handle_event_with(handler, decoy_conf, data, activity)

    def get_handler_configs(self, all_confs):
        canary_conf = None
        decoy_conf = None
        handler_confs = list()

        for handler_conf in all_confs:
            if handler_conf.model_type == ModelTypes.CANARY:
                canary_conf = handler_conf

            elif handler_conf.model_type == ModelTypes.DECOY:
                decoy_conf = handler_conf

            else:
                handler_confs.append(handler_conf)

        return handler_confs, canary_conf, decoy_conf

    def handle_event_with(self, handler: IHandler, conf: HandlerConf, data: dict, activity: Activity):
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
