import logging
import requests

from logistik.db import HandlerConf
from logistik.handlers import IHandlersManager
from logistik.handlers.request import Requester
from logistik.utils.exceptions import QueryException
from logistik.utils.exceptions import HandlerNotFoundException


class HandlersManager(IHandlersManager):
    def __init__(self, env):
        self.env = env
        self.requester = Requester()
        self.logger = logging.getLogger(__name__)
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

    def add_handler(self, handler_conf: HandlerConf):
        node_id = handler_conf.node_id()

        if handler_conf.event == 'UNMAPPED':
            try:
                self.query_model_for_info(handler_conf)
            except QueryException:
                # model is not online or doesn't implement query interface
                return

        if handler_conf.model_type is None:
            self.logger.info('not adding handler for empty model type with node id "{}"'.format(node_id))
            return

        if node_id in self.handlers:
            return

        self.logger.info('adding handler for node id "{}"'.format(node_id))
        from logistik.handlers.http import HttpHandler
        handler = HttpHandler.create(self.env, handler_conf)
        self.handlers[node_id] = handler

    def query_model_for_info(self, handler_conf: HandlerConf):
        url = f'http://{handler_conf.endpoint}:{handler_conf.port}/info'

        try:
            response = self.requester.request(method='GET', url=url)
        except Exception as e:
            # likely the model is offline
            raise QueryException(e)

        if response.status_code != 200:
            # likely doesn't implement the query interface
            raise QueryException(response.status_code)

        fields = ['return_to', 'event', 'method', 'retries', 'timeout', 'group_id', 'path', 'failed_topic']
        json_response = response.json()

        try:
            for field in fields:
                self.update_handler_value(handler_conf, json_response, field)
        except Exception as e:
            self.logger.error(f'could not update fields on handler with node_id {handler_conf.node_id()}: {str(e)}')
            raise QueryException(e)

        self.env.db.update_handler(handler_conf)

    def update_handler_value(self, handler_conf: HandlerConf, json_response: dict, field: str):
        if field not in json_response:
            return

        original = handler_conf.__getattribute__(field)
        updated = json_response.get(field)

        field_defaults = {
            'retries': 1,
            'timeout': 0
        }

        if field in field_defaults.keys():
            try:
                updated = int(float(updated))
            except ValueError:
                self.logger.warning('invalid value for "{}": "{}", will use default value of {}'.format(
                    field, updated, field_defaults[field])
                )
                updated = field_defaults[field]
        elif type(updated) != str:
            self.logger.warning('invalid value for "{}": "{}", not of type str but of "{}"'.format(
                field, updated, type(updated)
            ))
            return

        self.logger.info(f'updating field "{field}" from "{original}" to "{updated}"')
        handler_conf.__setattr__(field, updated)

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
