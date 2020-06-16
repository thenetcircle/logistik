import logging
import os
from uuid import uuid4 as uuid

from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix

from logistik import environ
from logistik.config import ConfigKeys
from logistik.environ import create_env, initialize_env
from logistik.utils.exceptions import QueryException

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
    config_paths = None
    if 'LK_CONFIG' in os.environ:
        config_paths = [os.environ['LK_CONFIG']]

    env = create_env(config_paths)
    initialize_env(env)

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
        template_folder='admin/templates/',
        static_folder='admin/static/'
    )
    env.cors = CORS(_app, resources={r"/api/*": {"origins": "*"}})

    _app.wsgi_app = ReverseProxied(ProxyFix(_app.wsgi_app))

    _app.config['ROOT_URL'] = env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB, default='/')
    _app.config['SECRET_KEY'] = secret
    _app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _app.config['SQLALCHEMY_POOL_SIZE'] = db_pool
    _app.config['SQLALCHEMY_DATABASE_URI'] = '{}://{}:{}@{}:{}/{}'.format(
        db_drvr, db_user, db_pass, db_host, db_port, db_name
    )

    logger.info('configuring db: {}'.format(_app.config['SQLALCHEMY_DATABASE_URI']))

    env.app = _app
    environ.env.app = _app

    with _app.app_context():
        env.dbman.init_app(_app)
        env.dbman.create_all()
        handlers = env.db.get_all_active_handlers()
        environ.init_event_reader(env, handlers)

    return _app, Api(_app)


def prepare_handler(env, handler_conf):
    node_id = handler_conf.node_id()

    if handler_conf.event == "UNMAPPED":
        try:
            query_model_for_info(env, handler_conf)
        except QueryException:
            pass

    if handler_conf.model_type is None:
        logger.info(
            f'not adding handler for empty model type with node id "{node_id}"'
        )
        return None

    return handler_conf


def query_model_for_info(env, handler_conf):
    env_name = ""
    if handler_conf.environment is not None:
        env_name = handler_conf.environment

    url = f"http://{handler_conf.endpoint}:{handler_conf.port}/info/{env_name}"

    try:
        response = env.requester.request(method="GET", url=url)
    except Exception as e:
        # likely the model is offline
        env.webhook.warning(f"could not query model /info: {str(e)}")
        raise QueryException(e)

    if response.status_code != 200:
        # likely doesn't implement the query interface
        env.webhook.warning(f"got error code {response.status_code} when querying /info")
        raise QueryException(response.status_code)

    fields = [
        "return_to",
        "event",
        "method",
        "retries",
        "timeout",
        "group_id",
        "path",
        "failed_topic",
    ]
    json_response = response.json()

    try:
        for field in fields:
            if field not in json_response:
                continue
            update_handler_value(handler_conf, json_response, field)

    except Exception as e:
        logger.error(
            f"could not update fields on handler with node_id {handler_conf.node_id()}: {str(e)}"
        )
        raise QueryException(e)

    env.db.update_handler(handler_conf)


def update_handler_value(
    handler_conf, json_response: dict, field: str
):
    original = handler_conf.__getattribute__(field)
    updated = json_response.get(field)

    field_defaults = {"retries": 1, "timeout": 0}

    if field in field_defaults.keys():
        try:
            updated = int(float(updated))
        except ValueError:
            logger.warning(
                f'invalid value for "{field}": "{updated}", using default: {field_defaults[field]}'
            )
            updated = field_defaults[field]
    elif type(updated) != str:
        logger.warning(
            f'invalid value for "{field}": "{updated}", not of type str but of "{type(updated)}"'
        )
        return

    logger.info(f'updating field "{field}" from "{original}" to "{updated}"')
    handler_conf.__setattr__(field, updated)


app, api = create_app()

# keep this, otherwise flask won't find any routes
# import logistik.admin.routes
