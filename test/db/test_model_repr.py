from unittest import TestCase

from logistik.db.models.handler import HandlerConfEntity


class ModelReprTest(TestCase):
    def setUp(self) -> None:
        self.conf = HandlerConfEntity(
            id='identity',
            name='name',
            service_id='service_id',
            enabled='enabled',
            retired='retired',
            event='event',
            endpoint='endpoint',
            hostname='hostname',
            port='port',
            version='version',
            path='path',
            node='node',
            method='method',
            retries='retries',
            model_type='model_type',
            group_id='group_id',
            timeout='timeout',
            tags='tags',
            event_display_name='event_display_name',
            return_to='return_to',
            failed_topic='failed_topic',
            startup='startup',
            traffic='traffic',
            reader_type='reader_type',
            reader_endpoint='reader_endpoint',
            consul_service_id='consul_service_id',
            environment='environment',
        )

    def test_entity_has_all_reprs(self):
        repr = self.conf.to_repr()
        for key in repr.__dict__.keys():
            if key == 'identity':
                continue
            self.assertEqual(repr.__getattribute__(key), self.conf.__getattribute__(key))

    def test_repr_has_all_entities(self):
        repr = self.conf.to_repr()
        for key in self.conf.__dict__.keys():
            if key == 'id' or key.startswith('_'):
                continue
            self.assertEqual(repr.__getattribute__(key), self.conf.__getattribute__(key))

    def test_entity_str_has_all_values(self):
        repr_str = str(self.conf)
        for key in self.conf.__dict__.keys():
            if key == 'id' or key.startswith('_'):
                continue
            self.assertIn('{}={}'.format(key, key), repr_str)
