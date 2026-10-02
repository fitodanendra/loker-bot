from datetime import datetime, timezone
from typing import Optional


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string (with 'Z', offset, or date only) into an aware UTC datetime."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
