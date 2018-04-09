import logging

from typing import List

from logistik.db import IDatabase
from logistik.environ import GNEnvironment
from logistik.handlers.base import BaseHandler
from logistik.db.models.handler import Handler

logger = logging.getLogger(__name__)


class DatabaseManager(IDatabase):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_enabled_handlers_for(self, event_name: str) -> List[BaseHandler]:
        handlers = Handler.query\
                .filter_by(event=event_name)\
                .filter_by(enabled=True)\
                .all()

        if handlers is None or len(handlers) == 0:
            logger.warning('no handler enabled for event {}'.format(event_name))
            return list()
        return handlers
