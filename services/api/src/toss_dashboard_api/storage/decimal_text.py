from decimal import Decimal

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import Text, TypeDecorator

from toss_dashboard_api.contracts.base import decimal_to_string, validate_decimal


class DecimalText(TypeDecorator[Decimal]):
    """Exact non-exponent Decimal storage for SQLite."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Decimal | str | None, _dialect: Dialect) -> str | None:
        if value is None:
            return None
        return decimal_to_string(validate_decimal(value))

    def process_result_value(self, value: str | None, _dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return validate_decimal(value)
