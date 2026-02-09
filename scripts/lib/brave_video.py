"""Brave Video Search for video content discovery."""

import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import brave_client, dates

# Depth config: (count, pages)
DEPTH_CONFIG = {
    "quick": (10, 1),
    "default": (20, 1),
    "deep": (20, 2),
}


def _log(msg: str):
    sys.stderr.write(f"[BRAVE-VIDEO] {msg}\n")
    sys.stderr.flush()


def _parse_page_age(page_age: Optional[str]) -> Optional[str]:
    """Parse Brave's page_age field to YYYY-MM-DD."""
    if not page_age:
        return None
    parsed = dates.parse_date(page_age)
    if parsed:
        return parsed.date().isoformat()
    match = re.match(r'(\d{4}-\d{2}-\d{2})', str(page_age))
    if match:
        return match.group(1)
    return None


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def search_videos(
    client: brave_client.BraveClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> Dict[str, Any]:
    """Search Brave Videos for content about the topic.

    Returns:
        Dict with 'results' key containing video results
    """
    freshness = f"{from_date}to{to_date}"
    count, pages = DEPTH_CONFIG.get(depth, (20, 1))

    all_results = []

    for page in range(pages):
        try:
            response = client.video_search(
                q=topic,
                freshness=freshness,
                count=count,
                offset=page,
            )
        except brave_client.BraveError as e:
            _log(f"Page {page} error: {e}")
            if page == 0:
                raise
            break

        results = response.get("results", [])
        all_results.extend(results)

        if not results or len(results) < count:
            break

    return {"results": all_results}


def parse_video_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Brave Video results into item dicts."""
    items = []
    results = response.get("results", [])

    total = len(results)
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            continue

        url = result.get("url", "")
        if not url:
            continue

        title = result.get("title", "").strip()
        description = result.get("description", "").strip()
        page_age = _parse_page_age(result.get("page_age"))
        source_domain = _extract_domain(url)

        # Extract thumbnail
        thumbnail_url = None
        thumbnail = result.get("thumbnail", {})
        if isinstance(thumbnail, dict):
            thumbnail_url = thumbnail.get("src")

        # Extract creator/publisher
        creator = None
        profile = result.get("profile", {})
        if isinstance(profile, dict):
            creator = profile.get("name") or profile.get("long_name")

        # Extract duration if available
        duration = None
        meta = result.get("video", {})
        if isinstance(meta, dict):
            duration = meta.get("duration")

        # Position-based relevance
        relevance = max(0.2, 1.0 - (i / max(total, 1)) * 0.8)

        items.append({
            "id": f"V{len(items)+1}",
            "title": title[:200],
            "url": url,
            "source_domain": source_domain,
            "creator": creator,
            "thumbnail_url": thumbnail_url,
            "duration": duration,
            "snippet": description[:300],
            "date": page_age,
            "relevance": relevance,
            "why_relevant": description[:150] if description else title[:150],
        })

    return items
