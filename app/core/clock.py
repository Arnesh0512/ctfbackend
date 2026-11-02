from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

LOCAL_TZ = ZoneInfo(settings.timezone)  # Asia/Kolkata (IST)


def istnow() -> datetime:
    """Return the current datetime in IST (Asia/Kolkata)."""
    return datetime.now(LOCAL_TZ)


def utcnow() -> datetime:
    """Return the current datetime in IST (Asia/Kolkata)."""
    return datetime.now(LOCAL_TZ)


def to_local(value: datetime | str | None) -> datetime | None:
    """Convert datetime or ISO string to configured local timezone (IST)."""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(LOCAL_TZ)


to_ist = to_local
