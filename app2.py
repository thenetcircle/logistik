import eventlet
eventlet.monkey_patch()

from second import app

from functools import partial
import random

pool = eventlet.GreenPool(10)


def call_handlers(data: dict, handlers):
    handler_func = partial(call_handler, data)
    threads = list()

    for handler in handlers:
        p = eventlet.spawn(handler_func, handler)
        threads.append(p)

    for p in threads:
        try:
            response = p.wait()
            print(f"response: {response}")
        except Exception as e:
            print(f"got exception: {str(e)}")


def call_handler(data: dict, handler_conf):
    import time

    time.sleep(random.random())

    if random.randint(0, 2) == 1:
        raise TimeoutError()

    return 200, handler_conf['name'], data


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
