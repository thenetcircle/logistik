from unittest import TestCase
from test.base import MockEnv
from logistik.enrich.manager import EnrichmentManager


class TestEnrichmentManager(TestCase):
    def setUp(self):
        self.env = MockEnv()
        self.manager = EnrichmentManager(self.env)

    def test_handle_adds_published(self):
        verb = 'test'
        data = {'verb': verb}

        response = self.manager.handle(data)

        self.assertIsNotNone(response.get('published', None), 'published not added to event')
        self.assertEqual(verb, data.get('verb', None), 'verb is not the same')

    def test_handle_adds_id(self):
        verb = 'test'
        data = {'verb': verb}

        response = self.manager.handle(data)

        self.assertIsNotNone(response.get('id', None), 'id not added to event')
        self.assertEqual(verb, data.get('verb', None), 'verb is not the same')
