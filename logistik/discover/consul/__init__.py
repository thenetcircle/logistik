from abc import ABC


class IConsulService(ABC):
    def get_services(self) -> list:
        """

        :return:
        """

    def get_service(self, name: str) -> dict:
        """

        :param name:
        :return:
        """
