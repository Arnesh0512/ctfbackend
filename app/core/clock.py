from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

LOCAL_TZ = ZoneInfo(settings.timezone)
IST = ZoneInfo("Asia/Kolkata")


def utcnow() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(UTC)


def now_utc() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(UTC)


def now_ist() -> datetime:
    """Return the current datetime in Indian Standard Time (IST)."""
    return datetime.now(IST)


def to_local(value: datetime) -> datetime:
    """Convert datetime to configured local timezone."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(LOCAL_TZ)


def to_ist(dt: datetime) -> datetime:
    """Convert any datetime object to Indian Standard Time (IST)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def format_ist(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str | None:
    """Format a datetime object into an IST string."""
    if dt is None:
        return None
    return to_ist(dt).strftime(fmt)
