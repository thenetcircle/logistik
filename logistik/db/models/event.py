from logistik.server import db
from logistik.db.repr.event import EventConf


class EventConfEntity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    event = db.Column(db.String(80), unique=False, nullable=False)
    enabled = db.Column(db.Boolean(), unique=False, nullable=False)
    instances = db.Column(db.Integer, unique=False, nullable=False, server_default=1)

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
