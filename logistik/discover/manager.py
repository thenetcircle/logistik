import consul
import time
import sys
import logging

from logistik.environ import GNEnvironment
from logistik.config import ConfigKeys
from logistik.discover.base import BaseDiscoveryService
from logistik.db.repr.handler import HandlerConf

logging.getLogger('urllib3').setLevel(logging.WARN)


class DiscoveryService(BaseDiscoveryService):
    SERVICE_ADDRESS = 'ServiceAddress'
    SERVICE_PORT = 'ServicePort'
    SERVICE_TAGS = 'ServiceTags'
    SERVICE_ID = 'ServiceID'

    def __init__(self, env: GNEnvironment):
        host = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DISCOVERY, default='127.0.0.1')
        port = env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DISCOVERY, default=8500)

        self.env = env
        self.consul = consul.Consul(host=host, port=port)
        self.logger = logging.getLogger(__name__)
        self.tag = env.config.get(ConfigKeys.TAG, domain=ConfigKeys.DISCOVERY, default='logistik')
        self.interval = env.config.get(ConfigKeys.INTERVAL, domain=ConfigKeys.DISCOVERY, default=30)

        if self.interval < 1:
            self.interval = 1
        elif self.interval > 3600:
            self.interval = 3600

    def poll_services(self):
        handlers = self.env.db.get_all_handlers()
        enabled_handlers_to_check = set()
        for handler in handlers:
            if not handler.enabled:
                continue
            enabled_handlers_to_check.add(handler.node_id())

        _, data = self.consul.catalog.services()
        for name, tags in data.items():
            if self.tag not in tags:
                continue

            _, services = self.consul.catalog.service(name)
            for service in services:
                service_id = service.get(DiscoveryService.SERVICE_ID)
                service_tags = service.get(DiscoveryService.SERVICE_TAGS)

                node, model_type = self.get_node_and_model_type_from_tags(service_tags)
                node_id = HandlerConf.to_node_id(service_id, model_type, node)

                if node_id in enabled_handlers_to_check:
                    enabled_handlers_to_check.remove(node_id)

                self.enable_handler(service, name)

        for node_id in enabled_handlers_to_check:
            self.disable_handler(node_id)

    def disable_handler(self, node_id: str):
        self.env.db.disable_handler(node_id)
        self.env.handlers_manager.stop_handler(node_id)

    def get_node_and_model_type_from_tags(self, tags):
        model_type = None
        node = None

        for tag in tags:
            if 'model=' in tag:
                model_type = tag.split('=', 1)[1]
            elif 'node=' in tag:
                node = tag.split('=', 1)[1]

        if model_type is None:
            self.logger.warning('no model type in tags')
        if node is None:
            self.logger.warning('no node number in tags')

        return node, model_type

    def enable_handler(self, service, name):
        host = service.get(DiscoveryService.SERVICE_ADDRESS)
        port = service.get(DiscoveryService.SERVICE_PORT)
        s_id = service.get(DiscoveryService.SERVICE_ID)
        tags = service.get(DiscoveryService.SERVICE_TAGS)
        node, model_type = self.get_node_and_model_type_from_tags(tags)

        if node is None or model_type is None:
            self.logger.info(service)
            return

        handler_conf = self.env.db.register_handler(host, port, s_id, name, node, model_type, tags)
        self.env.handlers_manager.start_handler(handler_conf.node_id())

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
