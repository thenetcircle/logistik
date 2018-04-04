# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
from base64 import b64encode
from typing import Union

import pkg_resources
import yaml

from recs.config import ConfigKeys
from recs.utils.decorators import timeit

ENV_KEY_ENVIRONMENT = 'RECS_ENVIRONMENT'
ENV_KEY_SECRETS = 'RECS_SECRETS'

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

        self.root_path = root_path
        self.config = config
        self.cache = None
        self.stats = None
        self.capture_exception = lambda e: False

        self.event_handler_map = dict()
        self.event_handlers = dict()


def b64e(s: str) -> str:
    if s is None:
        return ''

    s = s.strip()
    if len(s) == 0:
        return ''

    try:
        return str(b64encode(bytes(s, 'utf-8')), 'utf-8')
    except Exception as e:
        logger.error('could not b64encode because: %s, value was: \n%s' % (str(e), str(s)))
    return ''


def find_config(config_paths: list) -> tuple:
    default_paths = ["recs.yaml", "recs.json"]
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
                config_dict = yaml.load(open(path))
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
            secrets = yaml.load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


@timeit(logger, 'creating base environment')
def create_env(config_paths: list = None) -> GNEnvironment:
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
        config_dict[ConfigKeys.VERSION] = pkg_resources.require('recs')[0].version
    except Exception:
        # ignore, it will fail when running tests on CI because we don't include all requirements; no need
        pass

    config_dict[ConfigKeys.ENVIRONMENT] = gn_environment
    log_level = config_dict.get(ConfigKeys.LOG_LEVEL, ConfigKeys.DEFAULT_LOG_LEVEL)

    logging.basicConfig(
            level=getattr(logging, log_level),
            format=config_dict.get(ConfigKeys.LOG_FORMAT, ConfigKeys.DEFAULT_LOG_FORMAT))
    logging.getLogger('cassandra').setLevel(logging.WARNING)

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
        from recs.cache.redis import CacheRedis

        cache_host, cache_port = cache_engine.get(ConfigKeys.HOST), None
        if ':' in cache_host:
            cache_host, cache_port = cache_host.split(':', 1)

        cache_db = cache_engine.get(ConfigKeys.DB, 0)
        gn_env.cache = CacheRedis(gn_env, host=cache_host, port=cache_port, db=cache_db)
    elif cache_type == 'memory':
        from recs.cache.redis import CacheRedis
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
        from recs.stats.statsd import StatsDService
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

    dsn = gn_env.config.get(ConfigKeys.DSN, domain=ConfigKeys.LOGGING, default='')
    if dsn is None or len(dsn.strip()) == 0:
        logger.warning('sentry logging selected but no DSN supplied, not configuring sentry')
        return

    import raven
    import socket
    from git.cmd import Git

    home_dir = os.environ.get('RECS_HOME', default=None)
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


@timeit(logger, 'init plugins')
def init_plugins(gn_env: GNEnvironment):
    from yapsy.PluginManager import PluginManager
    logging.getLogger('yapsy').setLevel(gn_env.config.get(ConfigKeys.LOG_LEVEL, logging.INFO))

    plugin_manager = PluginManager()
    plugin_manager.setPluginPlaces(['recs/handlers'])
    plugin_manager.collectPlugins()

    for pluginInfo in plugin_manager.getAllPlugins():
        plugin_manager.activatePluginByName(pluginInfo.name)
        gn_env.event_handlers[pluginInfo.name] = pluginInfo.plugin_object

    handlers = gn_env.config.get(ConfigKeys.EVENT_HANDLERS, None)
    if handlers is None:
        return

    for key in handlers.keys():
        if key not in gn_env.event_handler_map:
            gn_env.event_handler_map[key] = list()
        plugins = handlers[key].copy()
        handlers[key] = dict()
        for plugin_info in plugins:
            plugin_name = plugin_info.get('name')
            handlers[key][plugin_name] = plugin_info
            try:
                gn_env.event_handler_map[key].append(gn_env.event_handlers[plugin_name])
            except KeyError:
                raise KeyError('specified plugin "{}" does not exist'.format(key))

    gn_env.config.set(ConfigKeys.EVENT_HANDLERS, handlers)

    for pluginInfo in plugin_manager.getAllPlugins():
        pluginInfo.plugin_object.setup(gn_env)


def initialize_env(recs_env):
    init_logging(recs_env)
    init_cache_service(recs_env)
    init_stats_service(recs_env)
    init_plugins(recs_env)


_config_paths = None
if 'RECS_CONFIG' in os.environ:
    _config_paths = [os.environ['RECS_CONFIG']]

env = create_env(_config_paths)
initialize_env(env)
