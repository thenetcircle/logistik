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
        stats.model_type = conf.model_type
        stats.node = conf.node
        stats.event = conf.event
        stats.name = conf.name
        stats.endpoint = conf.endpoint
        stats.version = conf.version
        stats.event_time = datetime.utcnow()
        stats.stat_type = stat_type

        if event is not None:
            stats.event_id = event.id
            stats.event_verb = event.verb
        else:
            stats.event_id = '<unknown>'
            stats.event_verb = '<unknown>'

        self.env.dbman.session.add(stats)
        self.env.dbman.session.commit()

    def failure(self, conf: HandlerConf, event: Activity=None) -> None:
        self.create(event, conf, HandlerStats.FAILURE)

    def success(self, conf: HandlerConf, event: Activity=None) -> None:
        self.create(event, conf, HandlerStats.SUCCESS)

    def error(self, conf: HandlerConf, event: Activity=None) -> None:
        self.create(event, conf, HandlerStats.ERROR)
