import logging
import sys

from logistik.config import ConfigKeys
from logistik.handlers.request import Requester
from logistik.utils import IWebHookHandler


class WebHookHandler(IWebHookHandler):
    def __init__(self, env):
        endpoint = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.WEBHOOK, default=None)
        channel_name = env.config.get(ConfigKeys.CHANNEL_NAME, domain=ConfigKeys.WEBHOOK, default=None)

        super().__init__(endpoint, channel_name)

        self.env = env
        self.logger = logging.getLogger(__name__)
        self.timeout = int(float(env.config.get(ConfigKeys.TIMEOUT, domain=ConfigKeys.WEBHOOK, default=10)))
        self.json_header = {"Context-Type": "application/json"}

    def _send_warning(self, message, topic_name=None, event_id=None) -> None:
        data = self._format("Warning", message, topic_name, event_id)
        self._send(data)

    def _send_critical(self, message, topic_name=None, event_id=None) -> None:
        data = self._format("Critical", message, topic_name, event_id)
        self._send(data)

    def _send_ok(self, message, topic_name=None, event_id=None) -> None:
        data = self._format("OK", message, topic_name, event_id)
        self._send(data)

    def _format(self, severity, message, topic_name, event_id):
        return {
            "channel": f"{self.channel_name}",
            "username": "Logistik",
            "text": f"""#### {severity}: Logistik is retrying handlers.
                    | Topic | Event | Failed Handlers |
                    |:-----------|:-----------:|:-----------------------------|
                    | {topic_name or '<unknown>'} | {event_id or '<unknown>'} | {message} | 
                    """
        }

    def _send(self, data: dict):
        try:
            response = Requester.request(
                method="POST", url=self.endpoint, json=data, headers=self.json_header, timeout=self.timeout
            )
        except Exception as e:
            self.logger.error(f"could not post to webhook '{self.endpoint}': {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
            return

        try:
            if response.status_code != 200:
                self.logger.error(f"got response code {response.status_code} when posting to webhook {self.endpoint}")
        except Exception as e:
            self.logger.error(f"could not check response code: {str(e)}")
            self.logger.exception(e)
            self.env.capture_exception(sys.exc_info())
