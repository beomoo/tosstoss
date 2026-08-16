from typing import Annotated, Self

from pydantic import StringConstraints, model_validator

from toss_dashboard_api.contracts.base import NormalizedRecord, SafeId
from toss_dashboard_api.contracts.enums import Jurisdiction

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Issuer(NormalizedRecord):
    issuer_id: SafeId
    legal_name: NonEmpty
    display_name: NonEmpty
    jurisdiction: Jurisdiction
    corp_code: str | None
    cik: str | None

    @model_validator(mode="after")
    def validate_identifiers(self) -> Self:
        self.require_missing_reasons("corp_code", "cik")
        if self.jurisdiction == Jurisdiction.KR and self.corp_code is None:
            raise ValueError("KR issuer requires a synthetic corp_code")
        if self.jurisdiction == Jurisdiction.US and self.cik is None:
            raise ValueError("US issuer requires a synthetic cik")
        return self
