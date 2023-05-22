import logging
from uuid import uuid4 as uuid

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from logistik import environ
from logistik.config import ConfigKeys

environ.initialize_env(environ.env, is_parent_process=True)

logger = logging.getLogger(__name__)
logging.getLogger("kafka.conn").setLevel(logging.INFO)
logging.getLogger("kafka.client").setLevel(logging.INFO)
logging.getLogger("kafka.metrics").setLevel(logging.INFO)


def create_app():
    _app = Flask(
        import_name=__name__,
        template_folder="admin/templates/",
        static_folder="admin/static/",
    )

    db_host = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DATABASE)
    db_port = int(environ.env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DATABASE))
    db_drvr = environ.env.config.get(ConfigKeys.DRIVER, domain=ConfigKeys.DATABASE)
    db_user = environ.env.config.get(ConfigKeys.USER, domain=ConfigKeys.DATABASE)
    db_pass = environ.env.config.get(ConfigKeys.PASS, domain=ConfigKeys.DATABASE)
    db_name = environ.env.config.get(ConfigKeys.NAME, domain=ConfigKeys.DATABASE)
    db_pool = int(
        environ.env.config.get(ConfigKeys.POOL_SIZE, domain=ConfigKeys.DATABASE)
    )
    secret = environ.env.config.get(ConfigKeys.SECRET_KEY, default=str(uuid()))
    root_url = environ.env.config.get(
        ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB, default="/"
    )

    _app.config["SECRET_KEY"] = secret
    _app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    _app.config["SQLALCHEMY_POOL_SIZE"] = db_pool
    _app.config["ROOT_URL"] = root_url
    _app.config["SQLALCHEMY_DATABASE_URI"] = "{}://{}:{}@{}:{}/{}".format(
        db_drvr, db_user, db_pass, db_host, db_port, db_name
    )

    return _app, SQLAlchemy(_app)


app, socketio = create_app()
# environ.init_web_auth(environ.env)

# keep this, otherwise flask won't find any routes
import logistik.admin.routes
