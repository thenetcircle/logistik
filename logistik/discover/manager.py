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
        from pprint import pprint

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'found {len(services)} consul service(s):')
            pprint(services)

        for name, tags in services.items():
            if f'{self.tag}={self.tag}' not in tags.get(DiscoveryService.SERVICE_TAGS):
                self.logger.debug(f'no "{self.tag}" in "{str(tags)}"')
                continue

            for service in services.values():
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

        handler_conf = self.env.db.register_handler(host, port, s_id, name, node, hostname, tags)
        self.env.handlers_manager.start_handler(handler_conf.node_id())
        return handler_conf

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
