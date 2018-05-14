import consul
import time
import sys
import logging

from logistik.environ import GNEnvironment
from logistik.config import ConfigKeys
from logistik.discover.base import BaseDiscoveryService

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
            enabled_handlers_to_check.add(handler.service_id)

        _, data = self.consul.catalog.services()
        for name, tags in data.items():
            if self.tag not in tags:
                continue

            _, services = self.consul.catalog.service(name)
            for service in services:
                service_id = service.get(DiscoveryService.SERVICE_ID)
                if service_id in enabled_handlers_to_check:
                    enabled_handlers_to_check.remove(service_id)

                self.enable_handler(service, name)

        for service_id in enabled_handlers_to_check:
            self.disable_handler(service_id)

    def disable_handler(self, service_id: str):
        self.env.db.disable_handler(service_id)
        self.env.handlers_manager.stop_handler(service_id)

    def enable_handler(self, service, name):
        host = service.get(DiscoveryService.SERVICE_ADDRESS)
        port = service.get(DiscoveryService.SERVICE_PORT)
        s_id = service.get(DiscoveryService.SERVICE_ID)
        tags = service.get(DiscoveryService.SERVICE_TAGS)

        handler_conf = self.env.db.register_handler(host, port, s_id, name, tags)
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
