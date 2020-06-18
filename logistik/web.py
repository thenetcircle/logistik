import logging
from uuid import uuid4 as uuid

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix

from logistik import environ
from logistik.config import ConfigKeys

environ.initialize_env(environ.env, is_parent_process=True)

logger = logging.getLogger(__name__)
logging.getLogger("kafka.conn").setLevel(logging.INFO)
logging.getLogger("kafka.client").setLevel(logging.INFO)
logging.getLogger("kafka.metrics").setLevel(logging.INFO)


class ReverseProxied(object):
    """
    Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    """

    def __init__(self, _app):
        self.app = _app

    def __call__(self, env, start_response):
        script_name = env.get("HTTP_X_SCRIPT_NAME", "")
        if script_name:
            env["SCRIPT_NAME"] = script_name
            path_info = env["PATH_INFO"]
            if path_info.startswith(script_name):
                env["PATH_INFO"] = path_info[len(script_name) :]

        scheme = env.get("HTTP_X_SCHEME", "")
        if scheme:
            env["wsgi.url_scheme"] = scheme
        return self.app(env, start_response)


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

    _app.wsgi_app = ReverseProxied(ProxyFix(_app.wsgi_app))

    return _app, SQLAlchemy(_app)


app, socketio = create_app()
# environ.init_web_auth(environ.env)

# keep this, otherwise flask won't find any routes
import logistik.admin.routes
