from logistik.db import HandlerConf
from logistik.environ import GNEnvironment
from logistik.handlers import IHandlerStats, IHandler


class HandlerStats(IHandlerStats):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def failure(self, handler: IHandler, conf: HandlerConf) -> None:
        pass

    def success(self, handler: IHandler, conf: HandlerConf) -> None:
        pass

    def error(self, handler: IHandler, conf: HandlerConf) -> None:
        pass
