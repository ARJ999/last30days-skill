"""Date utilities for last30days skill."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def get_date_range(days: int = 30) -> Tuple[str, str]:
    """Get the date range for the last N days.

    Returns:
        Tuple of (from_date, to_date) as YYYY-MM-DD strings
    """
    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=days)
    return from_date.isoformat(), today.isoformat()


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string in various formats.

    Supports: YYYY-MM-DD, ISO 8601, Unix timestamp
    """
    if not date_str:
        return None

    # Try Unix timestamp (from Reddit)
    try:
        ts = float(date_str)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    # Try ISO formats
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def timestamp_to_date(ts: Optional[float]) -> Optional[str]:
    """Convert Unix timestamp to YYYY-MM-DD string."""
    if ts is None:
        return None
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.date().isoformat()
    except (ValueError, TypeError, OSError):
        return None


def get_date_confidence(date_str: Optional[str], from_date: str, to_date: str) -> str:
    """Determine confidence level for a date.

    Args:
        date_str: The date to check (YYYY-MM-DD or None)
        from_date: Start of valid range (YYYY-MM-DD)
        to_date: End of valid range (YYYY-MM-DD)

    Returns:
        'high', 'med', or 'low'
    """
    if not date_str:
        return 'low'

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = datetime.strptime(from_date, "%Y-%m-%d").date()
        end = datetime.strptime(to_date, "%Y-%m-%d").date()

        if start <= dt <= end:
            return 'high'
        elif dt < start:
            # Older than range
            return 'low'
        else:
            # Future date (suspicious)
            return 'low'
    except ValueError:
        return 'low'


def days_ago(date_str: Optional[str]) -> Optional[int]:
    """Calculate how many days ago a date is.

    Returns None if date is invalid or missing.
    """
    if not date_str:
        return None

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        delta = today - dt
        return delta.days
    except ValueError:
        return None


def recency_score(date_str: Optional[str], max_days: int = 30) -> int:
    """Calculate recency score (0-100) with exponential freshness bias.

    Strongly prioritizes recent content:
    - Days 0-3: Premium tier (90-100) - Breaking/fresh content
    - Days 4-7: High tier (75-89) - This week's discussions
    - Days 8-14: Medium tier (50-74) - Recent but not fresh
    - Days 15-30: Low tier (10-49) - Still valid but aging
    - Beyond 30: Zero score

    This ensures "today's" content dominates over week-old content,
    matching user expectations for "latest" information.
    """
    age = days_ago(date_str)
    if age is None:
        return 0  # Unknown date gets worst score

    if age < 0:
        return 100  # Future date (treat as today)
    if age >= max_days:
        return 0

    # Exponential freshness bias with tiered scoring
    if age <= 1:
        # Today or yesterday: maximum freshness (98-100)
        return 100 - age * 2
    elif age <= 3:
        # Days 2-3: premium tier (92-96)
        return 96 - (age - 2) * 2
    elif age <= 7:
        # Days 4-7: high tier (76-90)
        return 90 - (age - 4) * 3.5
    elif age <= 14:
        # Days 8-14: medium tier (50-74)
        return 74 - (age - 8) * 3.4
    else:
        # Days 15-30: low tier (10-49)
        # Linear decay for the remaining range
        remaining = max_days - 15
        return int(49 - (age - 15) * (39 / remaining))


def recency_score_linear(date_str: Optional[str], max_days: int = 30) -> int:
    """Calculate linear recency score (0-100) - legacy method.

    0 days ago = 100, max_days ago = 0, clamped.
    """
    age = days_ago(date_str)
    if age is None:
        return 0

    if age < 0:
        return 100
    if age >= max_days:
        return 0

    return int(100 * (1 - age / max_days))
