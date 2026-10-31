from datetime import UTC, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    """Return the current datetime in Indian Standard Time (IST)."""
    return datetime.now(IST)


def now_utc() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(UTC)


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
