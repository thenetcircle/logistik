from abc import ABC, abstractmethod


class IWebHookHandler(ABC):
    def __init__(self, endpoint, channel_name):
        self.channel_name = channel_name
        self.endpoint = endpoint

        self.enabled = False
        if endpoint is not None and endpoint != '':
            self.enabled = True

    def warning(self, message, topic_name=None, event_id=None) -> None:
        if not self.enabled:
            return
        return self._send_warning(message, topic_name, event_id)

    def critical(self, message, topic_name=None, event_id=None) -> None:
        if not self.enabled:
            return
        return self._send_critical(message, topic_name, event_id)

    def ok(self, message, topic_name=None, event_id=None) -> None:
        if not self.enabled:
            return
        return self._send_ok(message, topic_name, event_id)

    @abstractmethod
    def _send_warning(self, message, topic_name=None, event_id=None) -> None:
        pass

    @abstractmethod
    def _send_critical(self, message, topic_name=None, event_id=None) -> None:
        pass

    @abstractmethod
    def _send_ok(self, message, topic_name=None, event_id=None) -> None:
        pass
