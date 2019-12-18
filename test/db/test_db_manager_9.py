from unittest import TestCase

from flask_sqlalchemy import SQLAlchemy

from logistik.db import HandlerConf
from logistik.utils.decorators import with_session
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
            environment = environ.env.dbman.Column(environ.env.dbman.String(), unique=False, nullable=True)

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

    def test_get_enabled_handler(self):
        self.assertEqual(0, len(self.db.get_all_enabled_handlers()))
