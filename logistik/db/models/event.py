from logistik.environ import env
from logistik.db.repr.event import EventConf


class EventConfEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    name = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    event = env.dbman.Column(env.dbman.String(80), unique=False, nullable=False)
    enabled = env.dbman.Column(env.dbman.Boolean(), unique=False, nullable=False)
    instances = env.dbman.Column(env.dbman.Integer(), unique=False, nullable=False, server_default='1')

    def to_repr(self) -> EventConf:
        return EventConf(
            identity=self.id,
            name=self.name,
            enabled=self.enabled,
            instances=self.instances
        )

    def __str__(self):
        return '<EventConfEntity id={}, name={}, event={}, enabled={}, instances={}>'.format(
            self.id, self.name, self.event, self.enabled, self.instances
        )
