from typing import Annotated, Self

from pydantic import StringConstraints, model_validator

from toss_dashboard_api.contracts.base import NonEmptyText, NormalizedRecord, SafeId
from toss_dashboard_api.contracts.enums import Jurisdiction

IssuerName = Annotated[NonEmptyText, StringConstraints(max_length=200)]


class Issuer(NormalizedRecord):
    issuer_id: SafeId
    legal_name: IssuerName
    display_name: IssuerName
    jurisdiction: Jurisdiction
    corp_code: NonEmptyText | None
    cik: NonEmptyText | None

    @model_validator(mode="after")
    def validate_identifiers(self) -> Self:
        self.require_missing_reasons("corp_code", "cik")
        if self.jurisdiction == Jurisdiction.KR and self.corp_code is None:
            raise ValueError("KR issuer requires a synthetic corp_code")
        if self.jurisdiction == Jurisdiction.US and self.cik is None:
            raise ValueError("US issuer requires a synthetic cik")
        return self
