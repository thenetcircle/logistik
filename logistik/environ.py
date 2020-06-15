import json
import logging
import os
from typing import Union
from typing import List
from typing import Tuple

import eventlet
import pkg_resources
import yaml

from logistik.config import ConfigKeys
from logistik.config import HandlerType
from logistik.discover.consul import IConsulService
from logistik.handlers import IHandlersManager
from logistik.enrich import IEnrichmentManager
from logistik.enrich import IEnricher
from logistik.stats import IStats
from logistik.cache import ICache
from logistik.queue import IKafkaWriter
from logistik.db import IDatabase
from logistik.utils.decorators import timeit

ENV_KEY_ENVIRONMENT = 'LK_ENVIRONMENT'
ENV_KEY_SECRETS = 'LK_SECRETS'

logger = logging.getLogger(__name__)


class ConfigDict:
    class DefaultValue:
        def __init__(self):
            pass

        def lower(self):
            raise NotImplementedError()

        def format(self):
            raise NotImplementedError()

    def __init__(self, params=None, override=None):
        self.params = params or dict()
        self.override = override

    def subp(self, parent):
        p = dict(parent.params)
        p.update(self.params)
        if self.override is not None:
            p.update(self.override)
        return ConfigDict(p, self.override)

    def sub(self, **params):
        p = dict(self.params)
        p.update(params)
        if self.override is not None:
            p.update(self.override)
        return ConfigDict(p, self.override)

    def set(self, key, val, domain: str=None):
        if domain is None:
            self.params[key] = val
        else:
            if domain not in self.params:
                self.params[domain] = dict()
            self.params[domain][key] = val

    def keys(self):
        return self.params.keys()

    def get(self, key, default: Union[None, object]=DefaultValue, params=None, domain=None):
        def config_format(s, _params):
            if s is None:
                return s

            if isinstance(s, list):
                return [config_format(r, _params) for r in s]

            if isinstance(s, dict):
                kw = dict()
                for k, v in s.items():
                    kw[k] = config_format(v, _params)
                return kw

            if not isinstance(s, str):
                return s

            if s.lower() == 'null' or s.lower() == 'none':
                return ''

            try:
                import re
                keydb = set('{' + key + '}')

                while True:
                    sres = re.search("{.*?}", s)
                    if sres is None:
                        break

                    # avoid using the same reference twice
                    if sres.group() in keydb:
                        raise RuntimeError(
                                "found circular dependency in config value '{0}' using reference '{1}'".format(
                                        s, sres.group()))
                    keydb.add(sres.group())
                    s = s.format(**_params)

                return s
            except KeyError as e:
                raise RuntimeError("missing configuration key: " + str(e))

        if params is None:
            params = self.params

        if domain is not None:
            if domain in self.params:
                # domain keys are allowed to be empty, e.g. for default amqp exchange etc.
                value = self.params.get(domain).get(key)
                if value is None:
                    if default is None:
                        return ''
                    return default

                return config_format(value, params)

        if key in self.params:
            return config_format(self.params.get(key), params)

        if default == ConfigDict.DefaultValue:
            raise KeyError(key)

        return config_format(default, params)

    def __contains__(self, key):
        if key in self.params:
            return True
        return False

    def __iter__(self):
        for k in sorted(self.params.keys()):
            yield k

    def __len__(self, *args, **kwargs):
        return len(self.params)


class GNEnvironment(object):
    def __init__(self, root_path: Union[str, None], config: ConfigDict, skip_init=False):
        """
        Initialize the environment
        """
        # can skip when testing
        if skip_init:
            return

        self.dbman = None
        self.app = None
        self.api = None
        self.root_path = root_path
        self.config = config
        self.cache: ICache = None
        self.db: IDatabase = None
        self.stats: IStats = None
        self.sql_alchemy_db = None
        self.failed_msg_log: logging.Logger = None
        self.dropped_msg_log: logging.Logger = None
        self.dropped_response_log: logging.Logger = None
        self.capture_exception = lambda e: False

        self.enrichment_manager: IEnrichmentManager = None
        self.enrichers: List[Tuple[str, IEnricher]] = list()

        self.handler_types: List[HandlerType] = list()
        self.handlers_manager: IHandlersManager = None
        self.kafka_writer: IKafkaWriter = None
        self.event_handler_map = dict()
        self.event_handlers = dict()
        self.consul: IConsulService = None


def find_config(config_paths: list) -> tuple:
    default_paths = ["config.yaml", "config.json"]
    config_dict = dict()
    config_path = None

    if config_paths is None:
        config_paths = default_paths

    for conf in config_paths:
        path = os.path.join(os.getcwd(), conf)

        if not os.path.isfile(path):
            continue

        try:
            if conf.endswith(".yaml"):
                config_dict = yaml.safe_load(open(path))
            elif conf.endswith(".json"):
                config_dict = json.load(open(path))
            else:
                raise RuntimeError("Unsupported file extension: {0}".format(conf))

        except Exception as e:
            raise RuntimeError("Failed to open configuration {0}: {1}".format(conf, str(e)))

        config_path = path
        break

    if not config_dict:
        raise RuntimeError('No configuration found: {0}\n'.format(', '.join(config_paths)))

    return config_dict, config_path


def load_secrets_file(config_dict: dict) -> dict:
    from string import Template
    import ast

    gn_env = os.getenv(ENV_KEY_ENVIRONMENT)
    secrets_path = os.getenv(ENV_KEY_SECRETS)
    if secrets_path is None:
        secrets_path = 'secrets/%s.yaml' % gn_env

    logger.debug('loading secrets file "%s"' % secrets_path)

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config_dict))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.safe_load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


@timeit(logger, 'creating base environment')
def create_env(config_paths: list = None, is_child_process: bool = False) -> GNEnvironment:
    logging.basicConfig(level='DEBUG', format=ConfigKeys.DEFAULT_LOG_FORMAT)

    gn_environment = os.getenv(ENV_KEY_ENVIRONMENT)
    logger.info('using environment %s' % gn_environment)

    # assuming tests are running
    if gn_environment is None:
        logger.debug('no environment found, assuming tests are running')
        return GNEnvironment(None, ConfigDict(dict()))

    config_dict, config_path = find_config(config_paths)
    config_dict = load_secrets_file(config_dict)

    try:
        config_dict[ConfigKeys.VERSION] = pkg_resources.require('logistik')[0].version
    except Exception:
        # ignore, it will fail when running tests on CI because we don't include all requirements; no need
        pass

    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    log_level = config_dict.get(ConfigKeys.LOG_LEVEL, ConfigKeys.DEFAULT_LOG_LEVEL)

    logging.basicConfig(
            level=getattr(logging, log_level),
            format=config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))

    if ConfigKeys.DATE_FORMAT not in config_dict:
        date_format = ConfigKeys.DEFAULT_DATE_FORMAT
        config_dict[ConfigKeys.DATE_FORMAT] = date_format
    else:
        from datetime import datetime
        date_format = config_dict[ConfigKeys.DATE_FORMAT]
        try:
            datetime.utcnow().strftime(date_format)
        except Exception as e:
            raise RuntimeError('invalid date format "{}": {}'.format(date_format, str(e)))

    if ConfigKeys.LOG_FORMAT not in config_dict:
        log_format = ConfigKeys.DEFAULT_LOG_FORMAT
        config_dict[ConfigKeys.LOG_FORMAT] = log_format

    if ConfigKeys.LOG_LEVEL not in config_dict:
        config_dict[ConfigKeys.LOG_LEVEL] = ConfigKeys.DEFAULT_LOG_LEVEL

    root_path = os.path.dirname(config_path)
    gn_env = GNEnvironment(root_path, ConfigDict(config_dict))

    logger.info('read config and created environment')
    return gn_env


@timeit(logger, 'init cache service')
def init_cache_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    cache_engine = gn_env.config.get(ConfigKeys.CACHE_SERVICE, None)

    if cache_engine is None:
        raise RuntimeError('no cache service specified')

    cache_type = cache_engine.get(ConfigKeys.TYPE, None)
    if cache_type is None:
        raise RuntimeError('no cache type specified, use one of [redis, mock]')

    if cache_type == 'redis':
        from logistik.cache.redis import CacheRedis

        cache_host, cache_port = cache_engine.get(ConfigKeys.HOST), None
        if ':' in cache_host:
            cache_host, cache_port = cache_host.split(':', 1)

        cache_db = cache_engine.get(ConfigKeys.DB, 0)
        gn_env.cache = CacheRedis(gn_env, host=cache_host, port=cache_port, db=cache_db)
    elif cache_type == 'memory':
        from logistik.cache.redis import CacheRedis
        gn_env.cache = CacheRedis(gn_env, host='mock')
    else:
        raise RuntimeError('unknown cache type %s, use one of [redis, mock]' % cache_type)


@timeit(logger, 'init stats service')
def init_stats_service(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    stats_engine = gn_env.config.get(ConfigKeys.STATS_SERVICE, None)

    if stats_engine is None:
        raise RuntimeError('no stats service specified')

    stats_type = stats_engine.get(ConfigKeys.TYPE, None)
    if stats_type is None:
        raise RuntimeError('no stats type specified, use one of [statsd] (set host to mock if no stats service wanted)')

    if stats_type == 'statsd':
        from logistik.stats.statsd import StatsDService
        gn_env.stats = StatsDService(gn_env)


@timeit(logger, 'init logging service')
def init_logging(gn_env: GNEnvironment) -> None:
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    logging_type = gn_env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.LOGGING, default='logger')
    if logging_type is None or len(logging_type.strip()) == 0 or logging_type in ['logger', 'default', 'mock']:
        return
    if logging_type != 'sentry':
        raise RuntimeError('unknown logging type %s' % logging_type)

    def _create_logger(_path: str, _name: str) -> logging.Logger:
        msg_formatter = logging.Formatter('%(asctime)s: %(message)s')
        msg_handler = logging.FileHandler(_path)
        msg_handler.setFormatter(msg_formatter)
        msg_logger = logging.getLogger(_name)
        msg_logger.setLevel(logging.INFO)
        msg_logger.addHandler(msg_handler)
        return msg_logger

    f_msg_path = gn_env.config.get(ConfigKeys.FAILED_MESSAGE_LOG, default='/tmp/logistik-failed-msgs.log')
    d_msg_path = gn_env.config.get(ConfigKeys.DROPPED_MESSAGE_LOG, default='/tmp/logistik-dropped-msgs.log')
    d_response_path = gn_env.config.get(ConfigKeys.DROPPED_RESPONSE_LOG, default='/tmp/logistik-dropped-responses.log')

    gn_env.failed_msg_log = _create_logger(f_msg_path, 'FailedMessages')
    gn_env.dropped_msg_log = _create_logger(d_msg_path, 'DroppedMessages')
    gn_env.dropped_response_log = _create_logger(d_response_path, 'DroppedResponses')

    dsn = gn_env.config.get(ConfigKeys.DSN, domain=ConfigKeys.LOGGING, default='')
    if dsn is None or len(dsn.strip()) == 0:
        logger.warning('sentry logging selected but no DSN supplied, not configuring sentry')
        return

    import raven
    import socket
    from git.cmd import Git

    home_dir = os.environ.get('LK_HOME', default=None)
    if home_dir is None:
        home_dir = '.'
    tag_name = Git(home_dir).describe()

    gn_env.sentry = raven.Client(
        dsn=dsn,
        environment=os.getenv(ENV_KEY_ENVIRONMENT),
        name=socket.gethostname(),
        release=tag_name
    )

    def capture_exception(e_info) -> None:
        try:
            gn_env.sentry.captureException(e_info)
        except Exception as e2:
            logger.exception(e_info)
            logger.error('could not capture exception with sentry: %s' % str(e2))

    gn_env.capture_exception = capture_exception


@timeit(logger, 'init web auth service')
def init_web_auth(gn_env: GNEnvironment) -> None:
    """
    manually invoked after app initialized
    """
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    web_auth_type = gn_env.config.get(ConfigKeys.TYPE, domain=ConfigKeys.WEB, default=None)
    if not web_auth_type or str(web_auth_type).strip().lower() in ['false', 'none', '']:
        logger.info('auth type was "{}", not initializing web auth'.format(web_auth_type))
        return

    if web_auth_type not in {'oauth'}:
        raise RuntimeError('unknown web auth type "{}", only "oauth" is available'.format(str(web_auth_type)))

    from logistik.admin.auth.oauth import OAuthService
    gn_env.web_auth = OAuthService(gn_env)
    logger.info('initialized OAuthService')


@timeit(logger, 'init db service')
def init_db_service(gn_env: GNEnvironment) -> None:
    from flask_sqlalchemy import SQLAlchemy
    gn_env.dbman = SQLAlchemy()

    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        gn_env.dbman = SQLAlchemy()
        return

    from logistik.db.manager import DatabaseManager
    gn_env.db = DatabaseManager(gn_env)


@timeit(logger, 'init enrichment service')
def init_enrichment_service(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    from logistik.enrich.manager import EnrichmentManager
    gn_env.enrichment_manager = EnrichmentManager(gn_env)

    # TODO: make enrichers configurable

    from logistik.enrich.published import PublishedEnrichment
    from logistik.enrich.identity import IdentityEnrichment

    gn_env.enrichers = [
        ('published', PublishedEnrichment()),
        ('id', IdentityEnrichment()),
    ]


@timeit(logger, 'init kafka writer service')
def init_kafka_writer(gn_env: GNEnvironment):
    if len(gn_env.config) == 0 or gn_env.config.get(ConfigKeys.TESTING, False):
        # assume we're testing
        return

    from logistik.queue.kafka_writer import KafkaWriter
    gn_env.kafka_writer = KafkaWriter(gn_env)
    gn_env.kafka_writer.setup()


@timeit(logger, 'init handlers manager')
def init_handlers_manager(gn_env: GNEnvironment) -> None:
    from logistik.handlers.manager import HandlersManager
    gn_env.handlers_manager = HandlersManager(gn_env)


@timeit(logger, 'init event handlers')
def init_event_handlers(gn_env: GNEnvironment):
    all_handlers = gn_env.db.get_all_handlers()
    event_handlers = dict()

    for handler in all_handlers:
        if handler.retired:
            continue

        if handler.event not in event_handlers:
            event_handlers[handler.event] = list()

        event_handlers[handler.event].append(handler)

    for event, handlers in event_handlers.items():
        gn_env.handlers_manager.start_event_handler(event, handlers)


@timeit(logger, 'init event reader')
def init_event_reader(gn_env: GNEnvironment):
    all_handlers = gn_env.db.get_all_handlers()
    gn_env.event_readers = dict()
    events = set()

    from logistik.handlers.event_reader import EventReader

    for handler in all_handlers:
        if handler.retired:
            continue

        events.add(handler.event)

    for event in events:
        reader = EventReader(event)
        process = eventlet.spawn(reader.run)
        gn_env.event_readers[event] = process


def initialize_env(lk_env):
    node_type = os.getenv("LK_NODE")

    init_logging(lk_env)
    init_cache_service(lk_env)
    init_stats_service(lk_env)
    init_enrichment_service(lk_env)

    if node_type == "reader":
        init_web_auth(lk_env)
        init_db_service(lk_env)
        init_kafka_writer(lk_env)
        init_event_reader(lk_env)

    elif node_type == "worker":
        init_handlers_manager(lk_env)
        init_event_handlers(lk_env)

    else:
        raise RuntimeError(f"unknown node type '{node_type}'")

    logger.info('startup done!')


_config_paths = None
if 'LK_CONFIG' in os.environ:
    _config_paths = [os.environ['LK_CONFIG']]

env = create_env(_config_paths)
initialize_env(env)