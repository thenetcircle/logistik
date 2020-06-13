import eventlet
eventlet.monkey_patch()

from functools import partial
import random

from flask import Flask

pool = eventlet.GreenPool(5)


def call_handlers(data: dict, handlers):
    handler_func = partial(call_handler, data)
    responses = list()

    for response in pool.imap(handler_func, handlers):
        print(f"response: {response}")
        responses.append(response)


def call_handler(data: dict, handler_conf):
    if random.randint(0, 2) == 1:
        raise TimeoutError()

    return 200, handler_conf['name'], data


app = Flask(
    import_name=__name__
)

call_handlers(
    {1: 2}, [
        {'name': 'handler-1'},
        {'name': 'handler-2'},
        {'name': 'handler-3'},
        {'name': 'handler-4'},
        {'name': 'handler-5'},
        {'name': 'handler-6'},
        {'name': 'handler-7'},
    ]
)
