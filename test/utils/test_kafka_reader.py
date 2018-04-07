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

    def test_parsing(self):
        class MockKafkaMessage(object):
            def __init__(self, msg):
                self.value = msg

        verb = 'foo'
        actor_id = 'bar'
        data = {
            'verb': verb,
            'actor': {'id': actor_id}
        }
        message = MockKafkaMessage(data)

        _, activity = self.reader.try_to_parse(message)

        self.assertEqual(verb, activity.verb)
        self.assertEqual(actor_id, activity.actor.id)
