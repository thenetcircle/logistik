from abc import ABC
from activitystreams import Activity
from logistik.db.repr.handler import HandlerConf


class IHandlersManager(ABC):
    def handle(self, data: dict, activity: Activity) -> None:
        """
        handle the event and possible tell the kafka writer to send a response

        :param data: the original event, before being parsed into a activity streams model
        :param activity: the incoming event in activity streams format
        :return: nothing
        """


class IHandler(ABC):
    def configure(self, conf: HandlerConf):
        raise NotImplementedError()

    def setup(self, env):
        raise NotImplementedError('setup() not implemented in plugin')

    def handle(self, data: dict, activity: Activity) -> tuple:
        raise NotImplementedError('handle() not implemented in plugin')

    def __call__(self, *args, **kwargs) -> (bool, str):
        raise NotImplementedError()
