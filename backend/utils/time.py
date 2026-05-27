from datetime import datetime, timezone

def utc_now() -> datetime:
    """Return current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    """Return current UTC datetime as an ISO-formatted string."""
    return utc_now().isoformat()
