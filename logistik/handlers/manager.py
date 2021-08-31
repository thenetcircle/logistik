import logging
from typing import List, Tuple

from logistik.db import HandlerConf
from logistik.handlers import IHandlersManager
from logistik.handlers.event_handler import EventHandler
from logistik.handlers.request import Requester


class HandlersManager(IHandlersManager):
    def __init__(self, env):
        self.env = env
        self.requester = Requester()
        self.logger = logging.getLogger(__name__)
        self.handler: EventHandler = None

    def handle_event(self, topic, event, span_ctx=None):
        if topic != self.handler.topic:
            self.logger.error(f"no handler configured for topic '{topic}'")
            return list()

        return self.handler.handle_event(event, span_ctx=None)

    def start_event_handler(self, topic: str, handlers: list, tracer=None):
        self.logger.info(f"starting handler for {topic}")
        self.handler = EventHandler(self.env, topic, handlers.copy(), tracer)
