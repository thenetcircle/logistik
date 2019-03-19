from logistik.environ import env


class IgnoreEntity(env.dbman.Model):
    id = env.dbman.Column(env.dbman.Integer(), primary_key=True)
    node_id = env.dbman.Column(env.dbman.String(128), unique=False, nullable=False)

    def __str__(self):
        return f'<IgnoreEntity id={self.id}, node_id={self.node_id}>'
