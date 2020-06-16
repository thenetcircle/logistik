import logging
from typing import List, Dict

from logistik.db import HandlerConf
from logistik.handlers import IHandlersManager
from logistik.handlers.event_handler import EventHandler
from logistik.handlers.request import Requester
from logistik.utils.exceptions import QueryException


class HandlersManager(IHandlersManager):
    def __init__(self, env):
        self.env = env
        self.requester = Requester()
        self.logger = logging.getLogger(__name__)
        self.handler: EventHandler = None

    def handle_event(self, topic, event) -> List[dict]:
        if topic != self.handler.topic:
            self.logger.error(f"no handler configured for topic '{topic}'")
            return list()

        return self.handler.handle_event(event)

    def start_event_handler(self, event: str, handlers: List[HandlerConf]):
        self.logger.info(f"starting handler for {event}")
        prepared_handlers = list()

        for handler_to_check in handlers:
            handler = self.prepare_handler(handler_to_check)

            if handler is not None:
                prepared_handlers.append(handler)

        self.handler = EventHandler(event, prepared_handlers.copy())

    def prepare_handler(self, handler_conf: HandlerConf):
        node_id = handler_conf.node_id()

        if handler_conf.event == "UNMAPPED":
            try:
                self.query_model_for_info(handler_conf)
            except QueryException:
                pass

        if handler_conf.model_type is None:
            self.logger.info(
                f'not adding handler for empty model type with node id "{node_id}"'
            )
            return None

        return handler_conf

    def query_model_for_info(self, handler_conf: HandlerConf):
        env_name = ""
        if handler_conf.environment is not None:
            env_name = handler_conf.environment

        url = f"http://{handler_conf.endpoint}:{handler_conf.port}/info/{env_name}"

        try:
            response = self.requester.request(method="GET", url=url)
        except Exception as e:
            # likely the model is offline
            self.env.webhook.warning(f"could not query model /info: {str(e)}")
            raise QueryException(e)

        if response.status_code != 200:
            # likely doesn't implement the query interface
            self.env.webhook.warning(f"got error code {response.status_code} when querying /info")
            raise QueryException(response.status_code)

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
        json_response = response.json()

        try:
            for field in fields:
                if field not in json_response:
                    continue
                self.update_handler_value(handler_conf, json_response, field)

        except Exception as e:
            self.logger.error(
                f"could not update fields on handler with node_id {handler_conf.node_id()}: {str(e)}"
            )
            raise QueryException(e)

        self.env.db.update_handler(handler_conf)

    def update_handler_value(
        self, handler_conf: HandlerConf, json_response: dict, field: str
    ):
        original = handler_conf.__getattribute__(field)
        updated = json_response.get(field)

        field_defaults = {"retries": 1, "timeout": 0}

        if field in field_defaults.keys():
            try:
                updated = int(float(updated))
            except ValueError:
                self.logger.warning(
                    f'invalid value for "{field}": "{updated}", using default: {field_defaults[field]}'
                )
                updated = field_defaults[field]
        elif type(updated) != str:
            self.logger.warning(
                f'invalid value for "{field}": "{updated}", not of type str but of "{type(updated)}"'
            )
            return

        self.logger.info(f'updating field "{field}" from "{original}" to "{updated}"')
        handler_conf.__setattr__(field, updated)
