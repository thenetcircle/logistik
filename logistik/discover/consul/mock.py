from logistik.discover.consul import IConsulService


class MockConsulService(IConsulService):
    def __init__(self, services: dict = None):
        self.services = services or dict()

    def get_service(self, name: str) -> tuple:
        return 0, dict(self.services.get(name, dict()))

    def get_services(self) -> tuple:
        return 0, dict(self.services)
