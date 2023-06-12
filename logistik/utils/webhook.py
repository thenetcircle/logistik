import logging
import sys

from logistik.config import ConfigKeys
from logistik.handlers.request import Requester
from logistik.utils import IWebHookHandler


def make_markdown_table(array, align: str =None):
    """
    modified from original here: https://gist.github.com/OsKaR31415/955b166f4a286ed427f667cb21d57bfd

    Args:
        array: The array to make into a table. Mush be a rectangular array
               (constant width and height).
        align: The alignment of the cells : 'left', 'center' or 'right'.
    """
    # make sure every element are strings
    array = [[str(elt) for elt in line] for line in array]

    # get the width of each column
    widths = [max(len(line[i]) for line in array) for i in range(len(array[0]))]

    # make every width at least 3 colmuns, because the separator needs it
    widths = [max(w, 3) for w in widths]

    # center text according to the widths
    array = [[elt.center(w) for elt, w in zip(line, widths)] for line in array]

    # separate the header and the body
    array_head, *array_body = array

    print(array_head)
    print()
    print()
    print(array_body)

    header = '| ' + ' | '.join(array_head) + ' |'

    # alignment of the cells
    align = str(align).lower()  # make sure `align` is a lowercase string

    if align == 'none':
        # we are just setting the position of the : in the table.
        # here there are none
        border_left = '| '
        border_center = ' | '
        border_right = ' |'

    elif align == 'center':
        border_left = '|:'
        border_center = ':|:'
        border_right = ':|'

    elif align == 'left':
        border_left = '|:'
        border_center = ' |:'
        border_right = ' |'

    elif align == 'right':
        border_left = '| '
        border_center = ':| '
        border_right = ':|'

    else:
        raise ValueError("align must be 'left', 'right' or 'center'.")

    separator = border_left + border_center.join(['-'*w for w in widths]) + border_right

    # body of the table
    body = [''] * len(array_body)  # empty string list that we fill after
    for idx, line in enumerate(array_body):
        # for each line, change the body at the correct index
        body[idx] = '| ' + ' | '.join(line) + ' |'
    body = '\n'.join(body)

    return header + '\n' + separator + '\n' + body


class WebHookHandler(IWebHookHandler):
    def __init__(self, env):
        endpoint = env.config.get(
            ConfigKeys.HOST, domain=ConfigKeys.WEBHOOK, default=None
        )

        super().__init__(endpoint)

        self.env = env
        self.logger = logging.getLogger(__name__)
        self.timeout = int(
            float(
                env.config.get(
                    ConfigKeys.TIMEOUT, domain=ConfigKeys.WEBHOOK, default=10
                )
            )
        )
        self.json_header = {"Context-Type": "application/json"}

    def _send_warning(self, message, topic_name=None, event_id=None) -> None:
        data = self._format("Warning", message, topic_name, event_id)
        self._send(data)

    def _send_critical(self, message, topic_name=None, event_id=None) -> None:
        data = self._format("Critical", message, topic_name, event_id)
        self._send(data)

    def _send_ok(self, message, topic_name=None, event_id=None, failed_handler_info=None) -> None:
        data = self._format("OK", message, topic_name, event_id, failed_handler_info)
        self._send(data)

    def _format(self, severity, message, topic_name, event_id, failed_handler_info=None):
        if failed_handler_info:
            handlers = make_markdown_table(failed_handler_info, align='center')

            return {
                "username": "Logistik",
                "text": f"#### {severity}: Logistik has issues with topic {topic_name or 'unknown'} and event ID {event_id or 'unknown'}: {message}.\n{handlers}",
            }
        else:
            return {
                "username": "Logistik",
                "text": f"#### {severity}: Logistik has issues.\n| Topic | Event | Failed Handlers |\n|:-----------|:-----------:|:-----------------------------|\n| {topic_name or 'unknown'} | {event_id or 'unknown'} | {message} |",
            }

    def _send(self, data: dict):
        try:
            response = Requester.request(
                method="POST",
                url=self.endpoint,
                json=data,
                headers=self.json_header,
                timeout=self.timeout,
                verbose=False
            )
        except Exception as e:
            self.logger.error(f"could not post to webhook '{self.endpoint}': {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            return

        try:
            if response.status_code != 200:
                self.logger.error(
                    f"got response code {response.status_code} when posting to webhook {self.endpoint}"
                )
        except Exception as e:
            self.logger.error(f"could not check response code: {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
