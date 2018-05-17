import logging

from logistik.environ import GNEnvironment
from logistik.handlers import IHandlersManager
from logistik.handlers.http import HttpHandler
from logistik.utils.exceptions import HandlerNotFoundException

logger = logging.getLogger(__name__)


class HandlersManager(IHandlersManager):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.handlers = dict()

    def setup(self):
        for handler_conf in self.env.db.get_all_enabled_handlers():
            self.add_handler(handler_conf)

    def get_handlers(self) -> list:
        def format_config(_node_id, config):
            _conf = {
                key: config.get(key, '') for key in [
                    'bootstrap_servers',
                    'group_id',
                    'auto_offset_reset',
                    'enable_auto_commit',
                    'max_poll_records',
                    'max_poll_interval_ms',
                    'session_timeout_ms'
                ]
            }
            _conf['node_id'] = _node_id
            return _conf

        return [
            format_config(
                node_id,
                self.handlers[node_id].reader.get_consumer_config()
            )
            for node_id in self.handlers
        ]

    def add_handler(self, handler_conf):
        node_id = handler_conf.node_id()

        if handler_conf.event == 'UNMAPPED':
            logger.info('not adding handler for unmapped event with node id "{}"'.format(node_id))
            return
        if handler_conf.model_type is None:
            logger.info('not adding handler for empty model type with node id "{}"'.format(node_id))
            return

        if node_id in self.handlers:
            return

        logger.info('adding handler for node id "{}"'.format(node_id))
        handler = HttpHandler.create(self.env, handler_conf)
        self.handlers[node_id] = handler

    def start_handler(self, node_id: str):
        try:
            conf = self.env.db.get_handler_for(node_id)
        except HandlerNotFoundException:
            return

        self.add_handler(conf)

    def stop_handler(self, node_id: str):
        handler = self.handlers.get(node_id)
        if handler is None:
            return

        handler.stop()
        del self.handlers[node_id]
