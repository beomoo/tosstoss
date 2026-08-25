"""Strict public data contracts."""

from toss_dashboard_api.contracts.base import CONTRACT_VERSION, StrictContract
from toss_dashboard_api.contracts.provider_identity import PROVIDER_IDENTITY_CONTRACT_VERSION
from toss_dashboard_api.contracts.provider_source import PROVIDER_SOURCE_CONTRACT_VERSION

__all__ = [
    "CONTRACT_VERSION",
    "PROVIDER_IDENTITY_CONTRACT_VERSION",
    "PROVIDER_SOURCE_CONTRACT_VERSION",
    "StrictContract",
]
