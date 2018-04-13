import logging
import os

from uuid import uuid4 as uuid
from flask import Flask
from flask_restful import Api

from logistik import environ
from logistik.config import ConfigKeys

logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'DEBUG')),
    format='%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s')


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

    _app = Flask(__name__)
    _app.config['SECRET_KEY'] = secret
    _app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _app.config['SQLALCHEMY_POOL_SIZE'] = db_pool
    _app.config['SQLALCHEMY_DATABASE_URI'] = '{}://{}:{}@{}:{}/{}'.format(
        db_drvr, db_user, db_pass, db_host, db_port, db_name
    )

    environ.env.app = _app
    environ.env.dbman.init_app(_app)

    return _app, Api(_app)


app, api = create_app()
# TODO: api.add_resource(SomeResource, '/some-path')
