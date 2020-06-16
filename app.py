# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from logistik.server import app, api

from logistik import environ
environ.env.node = 'app'
environ.env.api = api
environ.env.app = app
