class HandlerNotFoundException(Exception):
    pass


class HandlerExistsException(Exception):
    pass


class ParseException(Exception):
    pass


class QueryException(Exception):
    def __init__(self, status_code):
        self.status_code = status_code
