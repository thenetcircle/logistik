from unittest import TestCase

from flask_sqlalchemy import SQLAlchemy

from logistik.db import HandlerConf
from logistik.utils.decorators import with_session
from logistik.utils.exceptions import HandlerNotFoundException
from test.base import MockEnv
from flask import Flask

from logistik import environ
from logistik.db.manager import DatabaseManager

db = SQLAlchemy()


class TestDbManager(TestCase):
    def setUp(self):
        environ.env = MockEnv()
        environ.env.app = Flask(__name__)
        environ.env.app.config['TESTING'] = True
        environ.env.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        environ.env.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        environ.env.dbman = SQLAlchemy()
        environ.env.dbman.init_app(environ.env.app)
        environ.env.app.app_context().push()

        class HandlerConfEntity(environ.env.dbman.Model):
            id = environ.env.dbman.Column(environ.env.dbman.Integer(), primary_key=True)
            service_id = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            group_id = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=True)
            name = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            event = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            enabled = environ.env.dbman.Column(environ.env.dbman.Boolean(), unique=False, nullable=False)
            retired = environ.env.dbman.Column(environ.env.dbman.Boolean(), unique=False, nullable=False)
            endpoint = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            hostname = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            port = environ.env.dbman.Column(environ.env.dbman.Integer(), unique=False, nullable=False)
            version = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            path = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=True)
            node = environ.env.dbman.Column(environ.env.dbman.Integer(), unique=False, nullable=False)
            method = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=True)
            model_type = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            retries = environ.env.dbman.Column(environ.env.dbman.Integer(), unique=False, nullable=False)
            timeout = environ.env.dbman.Column(environ.env.dbman.Integer(), unique=False, nullable=False)
            tags = environ.env.dbman.Column(environ.env.dbman.String(256), unique=False, nullable=True)
            return_to = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=True)
            failed_topic = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=True)
            event_display_name = environ.env.dbman.Column(environ.env.dbman.String(128), unique=False, nullable=False)
            startup = environ.env.dbman.Column(environ.env.dbman.DateTime(), unique=False, nullable=True)
            traffic = environ.env.dbman.Column(environ.env.dbman.Float(), unique=False, nullable=False)
            reader_type = environ.env.dbman.Column(environ.env.dbman.String(), unique=False, nullable=False)
            reader_endpoint = environ.env.dbman.Column(environ.env.dbman.String(), unique=False, nullable=True)
            consul_service_id = environ.env.dbman.Column(environ.env.dbman.String(), unique=False, nullable=True)

        with environ.env.app.app_context():
            environ.env.dbman.create_all()
            environ.env.dbman.session.commit()
            self.session = environ.env.dbman.session

        self.db = DatabaseManager(environ.env)

    def tearDown(self):
        meta = environ.env.dbman.metadata
        for table in reversed(meta.sorted_tables):
            environ.env.dbman.session.execute(table.delete())

        environ.env.dbman.session.commit()

    def test_find_similar_handler(self):
        conf = HandlerConf(
            name='name', event='event', endpoint='endpoint', version='version',
            path='/path', model_type='model', node=0, timeout=60, retries=3,
            enabled=1, retired=0, service_id='serviceid', return_to='return',
            port=4444, hostname='hostname', traffic=0.1, reader_type='kafka',
            event_display_name='event'
        )

        self.assertIsNone(self.db.find_one_similar_handler(conf.service_id))
