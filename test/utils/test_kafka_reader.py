from test.base import BaseTest
from test.base import MockHandler

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

    def test_handle_mapped_event(self):
        event_name = 'existing'
        data = {
            'verb': event_name,
            'actor': {'id': 'foo'}
        }
        activity = parse(data)
        handler = MockHandler()
        handler.setup(self.env)
        self.env.event_handler_map[event_name] = [handler]

        # should not have handled anything yet
        self.assertEqual(0, handler.n_handled)

        # should be handled and NOT dropped
        self.reader.try_to_handle(data, activity)

        # should not have been dropped, and handler should have handled 1
        self.assertEqual(0, self.env.dropped_msg_log.drops)
        self.assertEqual(1, handler.n_handled)
