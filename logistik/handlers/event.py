import logging
import sys
import time
from typing import List

from logistik.db import HandlerConf
from logistik.environ import create_env


class EventHandler:
    def __init__(self, event: str, handlers: List[HandlerConf]):
        self.env = create_env(is_child_process=True)
        self.logger = logging.getLogger(__name__)
        self.event = event
        self.handlers = handlers
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            try:
                self.loop()
            except InterruptedError:
                self.logger.info("interrupted, shutting down")
                break
            except Exception as e:
                self.logger.error(f"for exception in loop: {str(e)}")
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                time.sleep(1)

    def loop(self):
        pass
