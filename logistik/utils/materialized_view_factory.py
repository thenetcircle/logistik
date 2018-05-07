from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement

from logistik import environ
db = environ.env.dbman


class CreateMaterializedView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


@compiler.compiles(CreateMaterializedView)
def compile_view(element, compiler, **kw):
    return 'CREATE MATERIALIZED VIEW %s AS %s' % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True))


def create_mat_view(name, selectable, metadata=db.metadata):
    # temp metadata just for initial Table object creation
    _mt = db.MetaData()

    # the actual mat view class is bound to db.metadata
    t = db.Table(name, _mt)
    for c in selectable.c:
        t.append_column(db.Column(c.name, c.type, primary_key=c.primary_key))

        db.event.listen(
            metadata, 'after_create',
            CreateMaterializedView(name, selectable)
        )

    db.event.listen(
        metadata, 'before_drop',
        db.DDL('DROP MATERIALIZED VIEW IF EXISTS ' + name)
    )

    return t
