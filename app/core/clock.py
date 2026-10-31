from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

LOCAL_TZ = ZoneInfo(settings.timezone)


def utcnow() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(UTC)


def to_local(value: datetime) -> datetime:
    """Convert datetime to configured local timezone."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(LOCAL_TZ)
