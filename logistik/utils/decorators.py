import time
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


def timeit(other_logger, tag: str):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            if other_logger is None:
                logger = this_logger
            else:
                logger = other_logger

            failed = False
            before = time.time()
            try:
                return view_func(*args, **kwargs)
            except Exception as e:
                failed = True
                logger.error('%s: %s' % (tag, str(e)))
                raise e
            finally:
                if not failed:
                    the_time = (time.time()-before)*1000
                    logger.debug('%s: %.2fms' % (tag, the_time))
        return decorator
    return factory
