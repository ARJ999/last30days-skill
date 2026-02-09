"""HackerNews search via Algolia API for developer community insights."""

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from . import http, dates


# HackerNews Algolia API - free, no authentication required
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

# Depth configurations: (min, max) stories to request
DEPTH_CONFIG = {
    "quick": (10, 15),
    "default": (20, 30),
    "deep": (40, 60),
}


def _log_error(msg: str):
    """Log error to stderr."""
    sys.stderr.write(f"[HN ERROR] {msg}\n")
    sys.stderr.flush()


def _log_info(msg: str):
    """Log info to stderr."""
    sys.stderr.write(f"[HN] {msg}\n")
    sys.stderr.flush()


def search_hn(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search HackerNews for relevant stories using Algolia API.

    Args:
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: Research depth - "quick", "default", or "deep"
        mock_response: Mock response for testing

    Returns:
        Raw API response
    """
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    # Convert dates to Unix timestamps for Algolia
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        from_ts = int(from_dt.timestamp())
        to_ts = int(to_dt.timestamp()) + 86400  # Include full end day
    except ValueError:
        from_ts = 0
        to_ts = int(datetime.now(timezone.utc).timestamp())

    # Build query parameters
    params = {
        "query": topic,
        "tags": "story",  # Only stories, not comments
        "numericFilters": f"created_at_i>{from_ts},created_at_i<{to_ts}",
        "hitsPerPage": max_items,
    }

    url = f"{HN_SEARCH_URL}?{urlencode(params)}"

    try:
        response = http.get(url, headers={"Accept": "application/json"}, timeout=30)
        return response
    except http.HTTPError as e:
        _log_error(f"Algolia API error: {e}")
        return {"error": str(e), "hits": []}
    except Exception as e:
        _log_error(f"Unexpected error: {e}")
        return {"error": str(e), "hits": []}


def parse_hn_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Algolia response to extract HackerNews items.

    Args:
        response: Raw API response

    Returns:
        List of item dicts
    """
    items = []

    if "error" in response and response["error"]:
        _log_error(f"HN API error in response: {response['error']}")
        return items

    hits = response.get("hits", [])

    for i, hit in enumerate(hits):
        if not isinstance(hit, dict):
            continue

        # Extract fields
        object_id = hit.get("objectID", "")
        title = hit.get("title", "")
        url = hit.get("url", "")
        story_url = f"https://news.ycombinator.com/item?id={object_id}"

        # Use external URL if available, otherwise HN discussion link
        if not url:
            url = story_url

        # Parse date from Unix timestamp
        created_at = hit.get("created_at_i")
        date_str = None
        if created_at:
            try:
                dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
                date_str = dt.date().isoformat()
            except (ValueError, TypeError, OSError):
                pass

        # Engagement metrics
        points = hit.get("points", 0) or 0
        num_comments = hit.get("num_comments", 0) or 0

        # Calculate relevance based on search ranking (Algolia already ranks by relevance)
        # Higher ranked items get higher relevance
        relevance = max(0.5, 1.0 - (i * 0.02))  # 1.0 down to 0.5

        item = {
            "id": f"HN{i+1}",
            "title": str(title).strip()[:200],
            "url": url,
            "hn_url": story_url,  # Always include HN discussion link
            "author": hit.get("author", ""),
            "date": date_str,
            "engagement": {
                "points": points,
                "num_comments": num_comments,
            },
            "relevance": relevance,
            "why_relevant": f"HackerNews story with {points} points and {num_comments} comments",
        }

        items.append(item)

    return items



# NOTE: HN engagement scoring is handled by score.compute_hn_engagement_raw()
# which operates on schema.Engagement objects (the canonical implementation).
