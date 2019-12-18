from enum import Enum


class ErrorCodes:
    """
    It indicates that the REST API successfully carried out whatever action the client
    requested and that no more specific code in the 2xx series is appropriate.
    """
    OK = 200

    """
    The 204 status code is usually sent out in response to a PUT, POST, or DELETE request
    when the REST API declines to send back any status message or representation in the
    response message’s body.
    """
    NO_CONTENT = 204

    UNKNOWN_ERROR = 250
    HANDLER_ERROR = 260
    HANDLER_DISABLED = 270

    RETRIES_EXCEEDED = 300

    """
    The 404 error status code indicates that the REST API can’t map the client’s URI to 
    a resource but may be available in the future. Subsequent requests by the client are 
    permissible.
    """
    NOT_FOUND = 404

    """
    If a model returns a 422 code it means it has already processed this event.
    """
    DUPLICATE_REQUEST = 422

    MISSING_ACTOR_ID = 500
    MISSING_OBJECT_ID = 501
    MISSING_TARGET_ID = 502
    MISSING_OBJECT_URL = 503
    MISSING_TARGET_DISPLAY_NAME = 504
    MISSING_ACTOR_URL = 505
    MISSING_OBJECT_CONTENT = 506
    MISSING_OBJECT = 507
    MISSING_OBJECT_ATTACHMENTS = 508
    MISSING_ATTACHMENT_TYPE = 509
    MISSING_ATTACHMENT_CONTENT = 510
    MISSING_VERB = 511

    INVALID_TARGET_TYPE = 600
    INVALID_STATUS = 604
    INVALID_OBJECT_TYPE = 605
    INVALID_BAN_DURATION = 606
    INVALID_VERB = 607


class HandlerType:
    def __init__(self, name: str, delay: float = 0.0, suffix=''):
        self.name = name
        self.delay = delay
        self.suffix = suffix


class StatsKeys(object):
    @staticmethod
    def handler_timing(node_id: str):
        return 'logistik.handler.{}'.format(node_id)


class HandlerKeys(object):
    HTTP = 'http'
    URL = 'url'
    METHOD = 'method'
    TIMEOUT = 'timeout'
    RETRIES = 'retries'
    NAME = 'name'


class ModelTypes(object):
    CANARY = 'canary'
    DECOY = 'decoy'
    MODEL = 'model'


class ServiceTags(object):
    NODE = 'node'
    HOSTNAME = 'hostname'
    MODEL = 'model'
    GROUP_ID = 'group_id'


class ConfigKeys(object):
    FAILED_MESSAGE_LOG = 'failed_msg_log'
    DROPPED_MESSAGE_LOG = 'dropped_msg_log'
    DROPPED_RESPONSE_LOG = 'dropped_response_log'
    LOG_LEVEL = 'log_level'
    LOG_FORMAT = 'log_format'
    DEBUG = 'debug'
    TESTING = 'testing'
    CACHE_SERVICE = 'cache'
    STATS_SERVICE = 'stats'
    DRIVER = 'driver'
    HOST = 'host'
    DSN = 'dsn'
    TYPE = 'type'
    PORT = 'port'
    PASS = 'password'
    USER = 'username'
    NAME = 'name'
    HOSTS = 'hosts'
    ZOOKEEPER = 'zookeeper'
    KAFKA = 'kafka'
    TOPIC = 'topic'
    LOGGING = 'logging'
    DATABASE = 'database'
    DB = 'db'
    POOL_SIZE = 'pool_size'
    DATE_FORMAT = 'date_format'
    PREFIX = 'prefix'
    EVENT_HANDLERS = 'handlers'
    MODEL_NAME = 'model_name'
    SECRET_KEY = 'secret'

    DISCOVERY = 'discovery'
    INTERVAL = 'interval'
    TAG = 'tag'

    HANDLER_TYPES = 'handler_types'
    DELAY = 'delay'
    SUFFIX = 'suffix'

    # for the admin interface
    ROOT_URL = 'root_url'
    WEB = 'web'
    USE_FLOATING_MENU = 'use_floating_menu'
    INSECURE = 'insecure'
    OAUTH_BASE = 'base'
    OAUTH_PATH = 'path'
    SERVICE_ID = 'service_id'
    SERVICE_SECRET = 'service_secret'
    AUTH_URL = 'authorized_url'
    TOKEN_URL = 'token_url'
    CALLBACK_URL = 'callback_url'
    UNAUTH_URL = 'unauthorized_url'
    OAUTH_ENABLED = 'enabled'

    # will be overwritten even if specified in config file
    ENVIRONMENT = '_environment'
    VERSION = '_version'

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
    DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    DEFAULT_LOG_LEVEL = 'INFO'


class RedisKeys(object):
    RKEY_AUTH = 'user:auth:%s'  # user:auth:user_id

    @staticmethod
    def auth_key(user_id: str) -> str:
        return RedisKeys.RKEY_AUTH % user_id
