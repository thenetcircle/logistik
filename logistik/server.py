import logging
import eventlet
import os

from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from logistik import environ
from logistik.config import ConfigKeys

logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'DEBUG')),
    format='%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s')


def create_app():
    db_host = environ.env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DATABASE)
    db_port = int(environ.env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DATABASE))
    db_drvr = environ.env.config.get(ConfigKeys.DRIVER, domain=ConfigKeys.DATABASE)
    db_user = environ.env.config.get(ConfigKeys.USER, domain=ConfigKeys.DATABASE)
    db_pass = environ.env.config.get(ConfigKeys.PASS, domain=ConfigKeys.DATABASE)
    db_name = environ.env.config.get(ConfigKeys.NAME, domain=ConfigKeys.DATABASE)
    db_pool = int(environ.env.config.get(ConfigKeys.POOL_SIZE, domain=ConfigKeys.DATABASE))

    _app = Flask(__name__)
    _app.config['SECRET_KEY'] = '60e17ba8-ef84-11e7-87cb-637e35b34927'
    _app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _app.config['SQLALCHEMY_POOL_SIZE'] = db_pool
    _app.config['SQLALCHEMY_DATABASE_URI'] = '{}://{}:{}@{}:{}/{}'.format(
        db_drvr, db_user, db_pass, db_host, db_port, db_name
    )

    return _app, Api(_app), SQLAlchemy(_app)


app, api, db = create_app()

# TODO: api.add_resource(SomeResource, '/some-path')
