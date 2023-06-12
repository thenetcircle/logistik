from logistik.utils.webhook import WebHookHandler, make_markdown_table
from test.base import BaseTest


class WebhookTests(BaseTest):
    def setUp(self):
        super().setUp(use_cache=False)
        self.webhook = WebHookHandler(self.env)

    def test_format(self):
        handler_info = [
            ["Name", "IP", "Port"],
            ["handler1", "ip1", 5565],
            ["handler2", "ip2", 6655],
            ['handler3new', "ip3", 4444]
        ]

        response = self.webhook._format("OK", "message", "topic", "event", handler_info)
        self.assertIsNotNone(response)

    def test_md_table(self):
        handler_info = [
            ["Name", "IP", "Port"],
            ["handler1", "ip", 5565],
            ["handler2", "ip2", 6655],
            ['handler3new', "ip1", 4444]
        ]

        response = make_markdown_table(handler_info, align='center')
        self.assertEqual(6, len(response.split("\n")))
