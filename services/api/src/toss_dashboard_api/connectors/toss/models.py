from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StrictInt,
    StrictStr,
    field_validator,
)

TOSS_ORIGIN = "https://openapi.tossinvest.com"
TOKEN_PATH = "/oauth2/token"
JSON_MEDIA_TYPE = "application/json"
FORM_MEDIA_TYPE = "application/x-www-form-urlencoded"
USER_AGENT = "toss-invest-dashboard/0.1.0"
OAUTH_RESPONSE_MAX_BYTES = 64 * 1024
MARKET_RESPONSE_MAX_BYTES = 32 * 1024 * 1024
REFRESHABLE_AUTH_CODES = frozenset({"expired-token", "invalid-token"})


class TossStaticEndpoint(StrEnum):
    STOCKS = "/api/v1/stocks"
    STOCKS_ALL = "/api/v1/stocks/all"
    PRICES = "/api/v1/prices"
    CANDLES = "/api/v1/candles"
    MARKET_CALENDAR_KR = "/api/v1/market-calendar/KR"
    MARKET_CALENDAR_US = "/api/v1/market-calendar/US"


class TossSymbolEndpoint(StrEnum):
    INVESTOR_TRADING = "/api/v1/stocks/{symbol}/investor-trading"
    PROGRAM_TRADES = "/api/v1/stocks/{symbol}/program-trades"
    SHORT_SELLING = "/api/v1/stocks/{symbol}/short-selling"
    CREDIT_TRADES = "/api/v1/stocks/{symbol}/credit-trades"
    SECURITIES_LENDING = "/api/v1/stocks/{symbol}/securities-lending"


QueryValue = str | int | bool
QueryParams = Mapping[str, QueryValue]

STATIC_QUERY_KEYS: Mapping[TossStaticEndpoint, frozenset[str]] = MappingProxyType(
    {
        TossStaticEndpoint.STOCKS: frozenset({"symbols"}),
        TossStaticEndpoint.STOCKS_ALL: frozenset(
            {"market", "status", "securityType", "commonShare"}
        ),
        TossStaticEndpoint.PRICES: frozenset({"symbols"}),
        TossStaticEndpoint.CANDLES: frozenset(
            {"symbol", "interval", "count", "before", "adjusted"}
        ),
        TossStaticEndpoint.MARKET_CALENDAR_KR: frozenset({"date"}),
        TossStaticEndpoint.MARKET_CALENDAR_US: frozenset({"date"}),
    }
)
SYMBOL_QUERY_KEYS = frozenset({"count", "until"})


class OAuthTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    access_token: SecretStr = Field(repr=False)
    token_type: Literal["Bearer"]
    expires_in: Annotated[StrictInt, Field(gt=0)]

    @field_validator("access_token")
    @classmethod
    def access_token_is_nonempty_and_header_safe(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value()
        if not token or any(ord(character) <= 32 or ord(character) == 127 for character in token):
            raise ValueError("access_token must be a non-empty bearer token")
        return value


OAuthErrorCode = Literal[
    "invalid_request",
    "invalid_client",
    "invalid_grant",
    "unauthorized_client",
    "unsupported_grant_type",
    "access_denied",
]


class OAuthErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    error: OAuthErrorCode
    error_description: StrictStr | None = None
    error_uri: StrictStr | None = None


class ProviderErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    requestId: StrictStr
    code: StrictStr
    message: StrictStr
    data: dict[str, object] | None = None


class ProviderErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    error: ProviderErrorDetail


KNOWN_PROVIDER_CODES = frozenset(
    {
        "edge-blocked",
        "edge-rate-limit-exceeded",
        "exchange-rate-not-found",
        "expired-token",
        "forbidden",
        "internal-error",
        "invalid-request",
        "invalid-token",
        "login-user-not-found",
        "maintenance",
        "rate-limit-exceeded",
        "stock-not-found",
        "unsupported-market",
        "unsupported-symbol",
    }
)


def safe_provider_code(value: str) -> str | None:
    return value if value in KNOWN_PROVIDER_CODES else None


def safe_request_id(value: str) -> str | None:
    if not 1 <= len(value) <= 64:
        return None
    if not all(
        character.isascii() and (character.isalnum() or character in "_-") for character in value
    ):
        return None
    return value
