from logistik.consul import IConsulService


class MockConsulService(IConsulService):
    def __init__(self, services: dict):
        self.services = services

    def get_service(self, name: str) -> dict:
        return dict(self.services.get(name, default=dict()))

    def get_services(self) -> list:
        return list(self.services.values())
