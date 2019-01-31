from abc import ABC


class IConsulService(ABC):
    def get_services(self) -> list:
        """
        returns:

            (index, {
                "consul": [],
                "redis": [],
                "postgresql": [
                    "master",
                    "slave"
                ]
            })

        metadata example:

            [
                'node=0', 'hostname=pc207', 'version=v0.1.2-9-g3bafd7f',
                'logistik', 'event=event-test-face', 'model=model'
            ]

        :return: a list of services' metadata
        """

    def get_service(self, name: str) -> dict:
        """
        returns:

            (index, [
                {
                    "Node": "foobar",
                    "Address": "10.1.10.12",
                    "ServiceID": "redis",
                    "ServiceName": "redis",
                    "ServiceTags": null,
                    "ServicePort": 8000
                }
            ])

        dict definition example:

            [{
                'Node': 'pc207',
                'Address': '10.60.0.23',
                'ServiceID': 'e40f3763',
                'ServiceName':
                'face',
                'ServiceTags': [
                    'logistik', 'event=event-test-face', 'model=model',
                    'node=0', 'hostname=pc207', 'version=v0.1.2-9-g3bafd7f'
                ],
                'ServiceAddress':
                '10.60.0.23',
                'ServicePort': 5151,
                'ServiceEnableTagOverride': False,
                'CreateIndex': 3979,
                'ModifyIndex': 3981
            }, {...}]

        :param name: name of the service
        :return: a list of dict definitions
        """
