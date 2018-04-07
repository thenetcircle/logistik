from test.base import BaseTest

from activitystreams import parse


class KafkaReaderTest(BaseTest):
    def setUp(self):
        super().setUp()

    def test_handle_unmapped_event(self):
        data = {
            'verb': 'non-existing',
            'actor': {'id': 'foo'}
        }
        activity = parse(data)

        # no drops should have occurred yet
        self.assertEqual(0, self.env.dropped_msg_log.drops)

        # should drop it since no handler exists for verb 'non-existing'
        self.reader.try_to_handle(data, activity)

        # reader should have dropped it since no mapping
        self.assertEqual(1, self.env.dropped_msg_log.drops)
