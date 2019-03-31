import consul

from logistik.config import ConfigKeys
from logistik.discover.consul import IConsulService
from logistik.environ import GNEnvironment


class ConsulService(IConsulService):
    def __init__(self, env: GNEnvironment):
        host = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DISCOVERY, default='127.0.0.1')
        port = env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DISCOVERY, default=8500)

        self.consul = consul.Consul(host=host, port=port)

    def get_service(self, name: str) -> dict:
        return self.consul.catalog.service(name)

    def get_services(self) -> list:
        return self.consul.catalog.services()

    def deregister(self, service_id: str) -> None:
        self.consul.agent.service.deregister(service_id)
