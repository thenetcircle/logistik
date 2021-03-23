from unittest import TestCase

from activitystreams import parse as parse_to_as

from logistik.handlers.event_handler import get_channels_for


class TestHandlers(TestCase):
    def test_channels_in_request(self):
        data = parse_to_as({
            "verb": "check", 
            "object": {
                "id": "3491881", 
                "url": "http://datamining.thenetcircle.lab:4445/data/robby.jpg"
            },
            "actor": {
                "id": "2448934"
            }, 
            "provider": {
                "id": "poppen"
            },
            "target": {
                "objectType": "channel", 
                "content": "[\"fsk\"]"
            }
        })

        response = get_channels_for(data)
        print(response)
