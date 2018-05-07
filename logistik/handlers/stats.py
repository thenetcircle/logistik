from logistik.db.models.handler import HandlerConf
from logistik.db.models.handler import HandlerStatsEntity
from logistik.environ import GNEnvironment
from logistik.handlers import IHandlerStats
from logistik.utils.decorators import with_session
from activitystreams import Activity

from datetime import datetime


class HandlerStats(IHandlerStats):
    FAILURE = 'failure'
    SUCCESS = 'success'
    ERROR = 'error'

    def __init__(self, env: GNEnvironment):
        self.env = env

    @with_session
    def create(self, event: Activity, conf: HandlerConf, stat_type: str) -> None:
        stats = HandlerStatsEntity()
        stats.service_id = conf.service_id
        stats.event = conf.event
        stats.name = conf.name
        stats.endpoint = conf.endpoint
        stats.version = conf.version
        stats.event_time = datetime.utcnow()
        stats.event_id = event.id
        stats.event_verb = event.verb
        stats.type = stat_type
        self.env.dbman.session.add(stats)
        self.env.dbman.session.commit()

    def failure(self, event: Activity, conf: HandlerConf) -> None:
        self.create(event, conf, HandlerStats.FAILURE)

    def success(self, event: Activity, conf: HandlerConf) -> None:
        self.create(event, conf, HandlerStats.SUCCESS)

    def error(self, event: Activity, conf: HandlerConf) -> None:
        self.create(event, conf, HandlerStats.ERROR)
