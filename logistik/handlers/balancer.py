import logging
import sys

from logistik.environ import GNEnvironment
from logistik.handlers import IHandlersManager
from logistik.handlers.http import HttpHandler
from logistik.utils.exceptions import HandlerNotFoundException
from logistik.utils.exceptions import HandlerExistsException

logger = logging.getLogger(__name__)


class HandlerBalancing(IHandlersManager):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.handlers = dict()

        for handler_conf in self.env.db.get_all_enabled_handlers():
            self.add_handler(handler_conf)

    def add_handler(self, handler_conf):
        if handler_conf.node_id() in self.handlers:
            raise HandlerExistsException(handler_conf.node_id())

        handler = HttpHandler.create(self.env, handler_conf)
        self.handlers[handler_conf.node_id()] = handler

    def start_handler(self, node_id: str):
        try:
            conf = self.env.db.get_handler_for(node_id)
        except HandlerNotFoundException:
            logger.error('no handler found for node id "{}"'.format(node_id))
            self.env.capture_exception(sys.exc_info())
            return

        self.add_handler(conf)

    def stop_handler(self, node_id: str):
        handler = self.handlers.get(node_id)
        handler.stop()
        del self.handlers[node_id]
