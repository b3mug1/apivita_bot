"""Display order times in the shop's local timezone."""

from datetime import datetime, timezone

import pytz


SHOP_TIMEZONE = pytz.timezone("Asia/Qyzylorda")


def format_local_datetime(value: datetime | str | None, pattern: str = "%d.%m.%Y %H:%M") -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(SHOP_TIMEZONE).strftime(pattern)
