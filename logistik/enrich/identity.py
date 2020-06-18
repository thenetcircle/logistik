from uuid import uuid4 as uuid

from logistik.enrich import IEnricher


class IdentityEnrichment(IEnricher):
    def __call__(self, *args, **kwargs) -> dict:
        data: dict = args[0]
        data["id"] = str(uuid())
        return data
