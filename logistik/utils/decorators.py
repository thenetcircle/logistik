import logging
from functools import wraps

from logistik import environ

this_logger = logging.getLogger(__name__)


def with_session(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        with environ.env.app.app_context():
            return view_func(*args, **kwargs)

    return wrapped
