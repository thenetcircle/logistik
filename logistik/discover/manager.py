import consul
import time
import sys
import logging

from logistik.environ import GNEnvironment
from logistik.config import ConfigKeys
from logistik.discover.base import BaseDiscoveryService

logging.getLogger('urllib3').setLevel(logging.WARN)


class DiscoveryService(BaseDiscoveryService):
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

    def register_handler(self, service, name):
        host = service.get('ServiceAddress')
        port = service.get('ServicePort')
        s_id = service.get('ServiceID')
        tags = service.get('ServiceTags')

        self.logger.info('registering service "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, s_id
        ))

        self.env.db.register_handler(host, port, s_id, name, tags)

    def poll_services(self):
        _, data = self.consul.catalog.services()
        for name, tags in data.items():
            if self.tag not in tags:
                continue

            _, services = self.consul.catalog.service(name)
            for service in services:
                self.register_handler(service, name)

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
