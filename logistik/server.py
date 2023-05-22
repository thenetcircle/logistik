import logging
import os
from uuid import uuid4 as uuid

from flask import Flask
from flask_restful import Api
from flask_cors import CORS

from logistik import environ
from logistik.config import ConfigKeys
from logistik.environ import create_env, initialize_env

log_level = os.environ.get("LOG_LEVEL", "DEBUG")
if log_level == "DEBUG":
    log_level = logging.DEBUG
elif log_level == "INFO":
    log_level = logging.INFO
elif log_level in {"WARNING", "WARN"}:
    log_level = logging.WARNING
else:
    log_level = logging.INFO

logging.basicConfig(
    level=log_level, format="%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.setLevel(log_level)
logging.getLogger("kafka").setLevel(logging.WARNING)
logging.getLogger("kafka.conn").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def create_app():
    config_paths = None
    if "LK_CONFIG" in os.environ:
        config_paths = [os.environ["LK_CONFIG"]]

    env = create_env(config_paths)
    initialize_env(env, is_parent_process=True)

    environ.env = env
    environ.env.dbman = env.dbman

    if len(env.config) == 0 or env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return None, None, None

    db_host = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DATABASE)
    db_port = int(env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DATABASE))
    db_drvr = env.config.get(ConfigKeys.DRIVER, domain=ConfigKeys.DATABASE)
    db_user = env.config.get(ConfigKeys.USER, domain=ConfigKeys.DATABASE)
    db_pass = env.config.get(ConfigKeys.PASS, domain=ConfigKeys.DATABASE)
    db_name = env.config.get(ConfigKeys.NAME, domain=ConfigKeys.DATABASE)
    db_pool = int(env.config.get(ConfigKeys.POOL_SIZE, domain=ConfigKeys.DATABASE))
    secret = env.config.get(ConfigKeys.SECRET_KEY, default=str(uuid()))

    _app = Flask(
        import_name=__name__,
        template_folder="admin/templates/",
        static_folder="admin/static/",
    )
    env.cors = CORS(_app, resources={r"/api/*": {"origins": "*"}})

    _app.config["ROOT_URL"] = env.config.get(
        ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB, default="/"
    )
    _app.config["SECRET_KEY"] = secret
    _app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    _app.config["SQLALCHEMY_POOL_SIZE"] = db_pool
    _app.config["SQLALCHEMY_DATABASE_URI"] = "{}://{}:{}@{}:{}/{}".format(
        db_drvr, db_user, db_pass, db_host, db_port, db_name
    )

    logger.info("configuring db: {}".format(_app.config["SQLALCHEMY_DATABASE_URI"]))

    env.app = _app
    environ.env.app = _app

    with _app.app_context():
        env.dbman.init_app(_app)
        env.dbman.create_all()
        handlers = env.db.get_all_active_handlers()
        environ.init_event_reader(env, handlers)

    return _app, Api(_app)


app, api = create_app()

# keep this, otherwise flask won't find any routes
# import logistik.admin.routes
