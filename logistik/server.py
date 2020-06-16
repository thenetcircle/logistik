import logging
import os
from uuid import uuid4 as uuid

from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix

from logistik import environ
from logistik.config import ConfigKeys


log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
if log_level == 'DEBUG':
    log_level = logging.DEBUG
elif log_level == 'INFO':
    log_level = logging.INFO
elif log_level in {'WARNING', 'WARN'}:
    log_level = logging.WARNING
else:
    log_level = logging.INFO

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(log_level)
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)


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
        script_name = env.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            env['SCRIPT_NAME'] = script_name
            path_info = env['PATH_INFO']
            if path_info.startswith(script_name):
                env['PATH_INFO'] = path_info[len(script_name):]

        scheme = env.get('HTTP_X_SCHEME', '')
        if scheme:
            env['wsgi.url_scheme'] = scheme
        return self.app(env, start_response)


def create_app():
    if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return None, None, None

    db_host = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DATABASE)
    db_port = int(environ.env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DATABASE))
    db_drvr = environ.env.config.get(ConfigKeys.DRIVER, domain=ConfigKeys.DATABASE)
    db_user = environ.env.config.get(ConfigKeys.USER, domain=ConfigKeys.DATABASE)
    db_pass = environ.env.config.get(ConfigKeys.PASS, domain=ConfigKeys.DATABASE)
    db_name = environ.env.config.get(ConfigKeys.NAME, domain=ConfigKeys.DATABASE)
    db_pool = int(environ.env.config.get(ConfigKeys.POOL_SIZE, domain=ConfigKeys.DATABASE))
    secret = environ.env.config.get(ConfigKeys.SECRET_KEY, default=str(uuid()))

    _app = Flask(
        import_name=__name__,
        template_folder='admin/templates/',
        static_folder='admin/static/'
    )
    environ.env.cors = CORS(_app, resources={r"/api/*": {"origins": "*"}})

    _app.wsgi_app = ReverseProxied(ProxyFix(_app.wsgi_app))

    _app.config['ROOT_URL'] = environ.env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB, default='/')
    _app.config['SECRET_KEY'] = secret
    _app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _app.config['SQLALCHEMY_POOL_SIZE'] = db_pool
    _app.config['SQLALCHEMY_DATABASE_URI'] = '{}://{}:{}@{}:{}/{}'.format(
        db_drvr, db_user, db_pass, db_host, db_port, db_name
    )

    logger.info('configuring db: {}'.format(_app.config['SQLALCHEMY_DATABASE_URI']))
    environ.env.app = _app
    with _app.app_context():
        environ.env.dbman.init_app(_app)
        environ.env.dbman.create_all()
        environ.init_event_reader(environ.env)
        environ.init_event_handlers(environ.env)

    return _app, Api(_app)


app, api = create_app()
environ.init_web_auth(environ.env)

# keep this, otherwise flask won't find any routes
import logistik.admin.routes
