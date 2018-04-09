from datetime import datetime

from logistik.config import ConfigKeys
from logistik.enrich import IEnricher


class PublishedEnrichment(IEnricher):
    def __call__(self, *args, **kwargs) -> dict:
        data: dict = args[0]

        # let the server determine the publishing time of the event, not the client
        # use default time format, since activity streams only accept RFC3339 format
        data['published'] = datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

        return data
