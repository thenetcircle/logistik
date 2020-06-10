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
    def get_all_activate_handlers(self) -> List[HandlerConf]:
        handlers = HandlerConfEntity.query\
            .filter_by(enabled=True, retired=False)\
            .all()

        return [handler.to_repr() for handler in handlers if handler.event != 'UNMAPPED']

    @with_session
    def delete_handler(self, node_id: str) -> None:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id, hostname=hostname, model_type=model_type, node=node
        ).first()

        if handler is None:
            logger.warning(
                f"no handler found for node ID {node_id} when calling delete_handler()"
            )
            return

        self.env.dbman.session.delete(handler)
        self.env.dbman.session.commit()

    @with_session
    def retire_model(self, node_id: str) -> None:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id, hostname=hostname, model_type=model_type, node=node
        ).first()

        if handler is None:
            logger.debug('handler with node id "{}" does not exist'.format(node_id))
            return

        logger.info("retiring {}".format(node_id))
        handler.retired = True
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

    @with_session
    def _promote_or_demote(
        self, node_id: str, type_str: str, new_model_type: str
    ) -> Union[HandlerConf, None]:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id, hostname=hostname, model_type=model_type, node=node
        ).first()

        if handler is None:
            logger.debug('handler with node id "{}" does not exist'.format(node_id))
            return None

        logger.info(f"{type_str} to {model_type} {node_id}")
        handler.model_type = new_model_type
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()
        return handler.to_repr()

    def demote_model(self, node_id: str) -> Union[HandlerConf, None]:
        return self._promote_or_demote(node_id, "demoting", ModelTypes.CANARY)

    def promote_canary(self, node_id: str) -> Union[HandlerConf, None]:
        return self._promote_or_demote(node_id, "promoting", ModelTypes.MODEL)

    def get_all_enabled_handlers(self):
        return self.get_all_handlers(only_enabled=True)

    @with_session
    def _enable_or_disable_handler(self, node_id: str, enable: bool):
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id, hostname=hostname, model_type=model_type, node=node
        ).first()

        if handler is None:
            logger.debug(f'handler with node id "{node_id}" does not exist')
            return

        if enable:
            logger.info(f'enabling handler with node id "{node_id}"')
        else:
            logger.info(f'disabling handler with node id "{node_id}"')

        handler.enabled = enable
        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        if handler.event != "UNMAPPED":
            self.env.cache.reset_enabled_handlers_for(handler.event)

    def enable_handler(self, node_id) -> None:
        self._enable_or_disable_handler(node_id, enable=True)

    def disable_handler(self, node_id) -> None:
        self._enable_or_disable_handler(node_id, enable=False)

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

    @with_session
    def get_handler_for(self, node_id: str) -> HandlerConf:
        service_id, hostname, model_type, node = HandlerConf.from_node_id(node_id)

        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id,
            hostname=hostname,
            model_type=model_type,
            node=node,
            retired=False,
        ).first()

        if handler is None:
            raise HandlerNotFoundException(node_id)
        return handler.to_repr()

    @with_session
    def get_handler_for_identity(self, identity: int) -> HandlerConf:
        handler = HandlerConfEntity.query.get(identity)

        if handler is None:
            raise HandlerNotFoundException(identity)
        return handler.to_repr()

    @with_session
    def find_one_handler(self, service_id, hostname, node) -> Union[HandlerConf, None]:
        handler = HandlerConfEntity.query.filter_by(
            service_id=service_id, hostname=hostname, node=node
        ).first()

        if handler is None:
            return None
        return handler.to_repr()

    @with_session
    def find_one_similar_handler(self, service_id):
        other_service_handler = HandlerConfEntity.query.filter_by(
            service_id=service_id
        ).first()

        if other_service_handler is None:
            return None
        return other_service_handler.to_repr()

    @with_session
    def register_handler(self, handler_conf: HandlerConf) -> HandlerConf:
        handler = HandlerConfEntity.query.filter_by(
            service_id=handler_conf.service_id,
            hostname=handler_conf.hostname,
            node=handler_conf.node,
        ).first()

        if handler is None:
            handler = HandlerConfEntity()

        handler.update(handler_conf)

        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        return handler.to_repr()

    @with_session
    def get_enabled_handlers_for(self, event_name: str) -> List[HandlerConf]:
        handlers = (
            HandlerConfEntity.query.filter_by(event=event_name)
            .filter_by(enabled=True)
            .all()
        )

        if handlers is None or len(handlers) == 0:
            logger.warning(f"no handler enabled for event {event_name}")
            return list()

        handler_reprs = list()
        for handler in handlers:
            handler_reprs.append(handler.to_repr())
        return handlers

    @with_session
    def update_consul_service_id_and_group_id(
        self, handler_conf: HandlerConf, consul_service_id: str, tags: dict
    ) -> HandlerConf:
        handler = HandlerConfEntity.query.filter_by(
            service_id=handler_conf.service_id,
            hostname=handler_conf.hostname,
            model_type=handler_conf.model_type,
            node=handler_conf.node,
        ).first()

        if handler is None:
            logger.warning(
                f"no handler found for HandlerConf: {handler_conf.to_json()}"
            )
            return handler_conf

        handler.consul_service_id = consul_service_id
        # handler.group_id = (
        #     tags.get(ServiceTags.GROUP_ID, None) or handler.service_id.split("-")[0]
        # )

        self.env.dbman.session.add(handler)
        self.env.dbman.session.commit()

        return handler.to_repr()
