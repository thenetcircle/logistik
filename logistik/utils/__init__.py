from logistik import environ


class ParseException(Exception):
    pass


def get_event_name(data: dict) -> str:
    try:
        return data['verb']
    except Exception:
        return 'unknown'


def increase_counter(data: dict, suffix: str) -> None:
    environ.env.stats.incr('{}-{}'.format(get_event_name(data), suffix))


def fail_message(data: dict) -> None:
    environ.env.failed_msg_log.info(data)
    increase_counter(data, 'failed')


def drop_message(data: dict) -> None:
    environ.env.dropped_msg_log.info(data)
    increase_counter(data, 'dropped')
