import datetime
from typing import Union

import time
import sys
import logging

from logistik.environ import GNEnvironment
from logistik.config import ConfigKeys, ModelTypes
from logistik.discover.base import BaseDiscoveryService
from logistik.db.repr.handler import HandlerConf

logging.getLogger('urllib3').setLevel(logging.WARN)


class DiscoveryService(BaseDiscoveryService):
    SERVICE_ADDRESS = 'ServiceAddress'
    SERVICE_PORT = 'ServicePort'
    SERVICE_TAGS = 'ServiceTags'
    SERVICE_NAME = 'ServiceName'

    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.tag = env.config.get(ConfigKeys.TAG, domain=ConfigKeys.DISCOVERY, default='logistik')
        self.interval = env.config.get(ConfigKeys.INTERVAL, domain=ConfigKeys.DISCOVERY, default=30)

        if self.interval < 1:
            self.interval = 1
        elif self.interval > 3600:
            self.interval = 3600

    def _get_enabled_handlers(self):
        handlers = self.env.db.get_all_handlers()
        enabled_handlers_to_check = set()

        for handler in handlers:
            if not handler.enabled:
                continue
            enabled_handlers_to_check.add(handler.node_id())

        return enabled_handlers_to_check

    def poll_services(self):
        enabled_handlers_to_check = self._get_enabled_handlers()
        _, services = self.env.consul.get_services()
        _, data = self.env.consul.get_services()

        for name, tags in data.items():
            if self.tag not in tags:
                continue

            _, services = self.env.consul.get_service(name)

            for service in services:
                service_id = service.get(DiscoveryService.SERVICE_NAME)
                service_tags = service.get(DiscoveryService.SERVICE_TAGS)

                model_type = ModelTypes.MODEL  # assuming it's a model initially
                node = self.get_from_tags('node', service_tags)
                hostname = self.get_from_tags('hostname', service_tags)
                node_id = HandlerConf.to_node_id(service_id, hostname, model_type, node)

                if node_id in enabled_handlers_to_check:
                    enabled_handlers_to_check.remove(node_id)

                handler_conf = self.enable_handler(service, name)
                if handler_conf is not None and handler_conf.node_id() in enabled_handlers_to_check:
                    enabled_handlers_to_check.remove(handler_conf.node_id())

        for node_id in enabled_handlers_to_check:
            handlers_str = ",".join(enabled_handlers_to_check)
            self.logger.debug(f'node {node_id} from consul not in db [{handlers_str}], disabling')
            self.disable_handler(node_id)

    def disable_handler(self, node_id: str):
        self.env.db.disable_handler(node_id)
        self.env.handlers_manager.stop_handler(node_id)

    def get_from_tags(self, key, tags):
        value = None

        for tag in tags:
            if '{}='.format(key) in tag:
                value = tag.split('=', 1)[1]

        if value is None:
            self.logger.warning('no "{}" in tags: {}'.format(key, tags))

        return value

    def enable_handler(self, service, name) -> Union[HandlerConf, None]:
        host = service.get(DiscoveryService.SERVICE_ADDRESS)
        port = service.get(DiscoveryService.SERVICE_PORT)
        s_id = service.get(DiscoveryService.SERVICE_NAME)
        tags = service.get(DiscoveryService.SERVICE_TAGS)

        node = self.get_from_tags('node', tags)
        hostname = self.get_from_tags('hostname', tags)

        if node is None or hostname is None:
            self.logger.error('missing node/hostname in: {}'.format(service))
            return None

        handler_conf = self.create_or_update_handler(host, port, s_id, name, node, hostname, tags)
        self.env.db.register_handler(handler_conf)

        if handler_conf.event != 'UNMAPPED':
            self.env.cache.reset_enabled_handlers_for(handler_conf.event)

        self.env.handlers_manager.start_handler(handler_conf.node_id())
        return handler_conf

    def create_or_update_handler(self, host, port, service_id, name, node, hostname, tags):
        handler = self.env.db.find_one_handler(service_id, hostname, node)

        tags_dict = dict()
        for tag in tags:
            if '=' not in tag:
                continue
            k, v = tag.split('=', maxsplit=1)
            tags_dict[k] = v

        if handler is not None:
            return self._update_existing_handler(handler, service_id, node, name, hostname, port, host, tags_dict)
        return self._create_new_handler(service_id, node, name, hostname, port, host, tags_dict)

    def _update_existing_handler(
            self, handler: HandlerConf, service_id, node, name, hostname, port, host, tags_dict: dict
    ):
        if handler.enabled:
            return handler

        self.logger.info('registering updated handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))

        return self._create_handler(handler, service_id, node, name, hostname, port, host, tags_dict)

    def _create_new_handler(self, service_id, node, name, hostname, port, host, tags_dict: dict):
        self.logger.info('registering new handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))

        handler = self._create_handler(HandlerConf(), service_id, node, name, hostname, port, host, tags_dict)
        other_service_handler = self.env.db.find_one_similar_handler(service_id)

        # copy known values form previous handler
        if other_service_handler is not None:
            if 'event' not in tags_dict.keys():
                handler.event = other_service_handler.event
            if 'path' not in tags_dict.keys():
                handler.path = other_service_handler.path
            if 'method' not in tags_dict.keys():
                handler.method = other_service_handler.method

        handler.model_type = ModelTypes.CANARY
        handler.enabled = False
        return handler

    def _create_handler(
            self, handler: HandlerConf, service_id, node, name, hostname, port, host, tags_dict: dict
    ):
        handler.enabled = True
        handler.startup = datetime.datetime.utcnow()
        handler.name = name
        handler.service_id = service_id
        handler.version = tags_dict.get('version', None) or handler.version
        handler.path = tags_dict.get('path', None) or handler.path
        handler.event = tags_dict.get('event', handler.event) or 'UNMAPPED'
        handler.return_to = tags_dict.get('returnto', None) or handler.return_to
        handler.reader_type = tags_dict.get('readertype', handler.reader_type) or 'kafka'
        handler.reader_endpoint = tags_dict.get('readerendpoint', None) or handler.reader_endpoint
        handler.model_type = ModelTypes.MODEL
        handler.node = node
        handler.hostname = hostname
        handler.endpoint = host
        handler.port = port

        return handler

    def run(self):
        while True:
            try:
                self.poll_services()
            except InterruptedError:
                self.logger.info('interrupted, shutting down')
                break
            except Exception as e:
                self.logger.error('could not poll service, sleeping for 3 seconds: {}'.format(str(e)))
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())

            time.sleep(self.interval)
