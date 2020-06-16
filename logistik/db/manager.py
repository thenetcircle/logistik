import logging
from typing import List
from typing import Union

from logistik.config import ModelTypes, ServiceTags
from logistik.db import IDatabase
from logistik.db.models.handler import HandlerConfEntity
from logistik.db.reprs.handler import HandlerConf
from logistik.environ import GNEnvironment
from logistik.utils.decorators import with_session
from logistik.utils.exceptions import HandlerNotFoundException

logger = logging.getLogger(__name__)


class DatabaseManager(IDatabase):
    def __init__(self, env: GNEnvironment):
        self.env = env

    @with_session
    def get_all_handlers(
        self, include_retired=False, only_enabled=False
    ) -> List[HandlerConf]:
        if only_enabled:
            handlers = HandlerConfEntity.query.filter_by(enabled=True).all()
        elif include_retired:
            handlers = HandlerConfEntity.query.all()
        else:
            handlers = HandlerConfEntity.query.filter_by(retired=False).all()

        return [handler.to_repr() for handler in handlers]

    @with_session
    def get_all_active_handlers(self) -> List[HandlerConf]:
        handlers = HandlerConfEntity.query.filter_by(retired=False).all()

        return [
            handler.to_repr() for handler in handlers if handler.event != "UNMAPPED"
        ]

    @with_session
    def update_handler(self, handler_conf: HandlerConf):
        service_id, hostname, model_type, node = HandlerConf.from_node_id(
            handler_conf.node_id()
        )

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id, hostname=hostname, model_type=model_type, node=node
        ).first()

        if handler is None:
            logger.debug(
                f'handler with node id "{handler_conf.node_id()}" does not exist'
            )
            return

        fields = [
            "return_to",
            "event",
            "method",
            "retries",
            "timeout",
            "group_id",
            "path",
            "failed_topic",
        ]
        for field in fields:
            updated = handler_conf.__getattribute__(field)
            handler.__setattr__(field, updated)

        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()
