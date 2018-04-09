from logistik.server import db
from logistik.db.repr.handler import HandlerConf


class HandlerConfEntity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    event = db.Column(db.String(80), unique=False, nullable=False)
    enabled = db.Column(db.Boolean(), unique=False, nullable=False)
    endpoint = db.Column(db.String(80), unique=False, nullable=False)
    version = db.Column(db.String(16), unique=False, nullable=False, server_default='v1')
    path = db.Column(db.String(80), unique=False, nullable=False)
    node = db.Column(db.Integer, unique=False, nullable=False, server_default=0)

    def to_repr(self) -> HandlerConf:
        return HandlerConf(
            identity=self.id,
            name=self.name,
            enabled=self.enabled,
            endpoint=self.endpoint,
            version=self.version,
            path=self.path,
            node=self.node
        )

    def __str__(self):
        return '<HandlerConfEntity id={}, name={}, event={}, enabled={}, endpoint={}, version={}, path={}>'.format(
            self.id, self.name, self.event, self.enabled, self.endpoint, self.version, self.path
        )
