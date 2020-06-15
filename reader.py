import eventlet

# need to monkey patch some standard functions in python since they don't natively support async mode
eventlet.monkey_patch()

import os

node_type = "reader"
os.environ["LK_NODE"] = node_type

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from logistik.server import app, api

from logistik import environ
environ.env.node = node_type
environ.env.api = api
environ.env.app = app
