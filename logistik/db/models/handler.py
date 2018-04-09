from logistik.server import db


class HandlerConf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    event = db.Column(db.String(80), unique=False, nullable=False)
    enabled = db.Column(db.Boolean(), unique=False, nullable=False)
    endpoint = db.Column(db.String(80), unique=False, nullable=False)
    version = db.Column(db.String(16), unique=False, nullable=False, server_default='v1')
    path = db.Column(db.String(80), unique=False, nullable=False)
    node = db.Column(db.Integer, unique=False, nullable=False, server_default=0)

    def __str__(self):
        return '<Handler id={}, name={}, event={}, enabled={}, endpoint={}, version={}, path={}>'.format(
            self.id, self.name, self.event, self.enabled, self.endpoint, self.version, self.path
        )
