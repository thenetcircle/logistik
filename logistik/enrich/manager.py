from logistik.environ import GNEnvironment
from logistik.enrich import IEnrichmentManager
from logistik.utils import ParseException


class EnrichmentManager(IEnrichmentManager):
    def __init__(self, env: GNEnvironment):
        self.env: GNEnvironment = env

    def handle(self, data: dict) -> dict:
        event_name = data.get('verb', None)
        if event_name is None:
            raise ParseException('no verb in event: {}'.format(str(data)))

        enriched = data.copy()
        for _, enrich in self.env.enrichers:
            enriched = enrich(enriched)
        return enriched
