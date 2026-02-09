"""Brave News Search for news article discovery."""

import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import brave_client, dates

# Depth config: count per page (news supports up to 50)
DEPTH_CONFIG = {
    "quick": (20, 1),     # 20 results, 1 page
    "default": (50, 1),   # 50 results, 1 page
    "deep": (50, 2),      # 50 results, 2 pages
}


def _log(msg: str):
    sys.stderr.write(f"[BRAVE-NEWS] {msg}\n")
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


def _extract_source_name(result: Dict) -> str:
    """Extract human-readable source name from Brave news result."""
    # Try meta_url first
    meta_url = result.get("meta_url", {})
    if isinstance(meta_url, dict):
        hostname = meta_url.get("hostname", "")
        if hostname:
            return hostname.removeprefix("www.")

    # Try profile
    profile = result.get("profile", {})
    if isinstance(profile, dict) and profile.get("name"):
        return profile["name"]

    # Fall back to domain extraction
    return _extract_domain(result.get("url", ""))


def search_news(
    client: brave_client.BraveClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> Dict[str, Any]:
    """Search Brave News for articles about the topic.

    Returns:
        Dict with 'results' key containing news results
    """
    freshness = f"{from_date}to{to_date}"
    count, pages = DEPTH_CONFIG.get(depth, (50, 1))

    all_results = []

    for page in range(pages):
        try:
            response = client.news_search(
                q=topic,
                freshness=freshness,
                count=count,
                offset=page,
                extra_snippets=True,
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


def parse_news_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Brave News results into item dicts."""
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
        extra_snippets = result.get("extra_snippets", [])
        page_age = _parse_page_age(result.get("page_age"))
        source_name = _extract_source_name(result)
        source_domain = _extract_domain(url)

        # If page_age is missing, try 'age' field (human-readable)
        if not page_age:
            age_str = result.get("age", "")
            if age_str:
                # Brave sometimes provides "2 hours ago" etc. - not parseable to date
                # In this case, date_confidence drops
                pass

        # Position-based relevance
        relevance = max(0.2, 1.0 - (i / max(total, 1)) * 0.8)

        items.append({
            "id": f"N{len(items)+1}",
            "title": title[:200],
            "url": url,
            "source_name": source_name,
            "source_domain": source_domain,
            "snippet": description[:300],
            "extra_snippets": [s[:200] for s in (extra_snippets or [])[:5]],
            "date": page_age,
            "relevance": relevance,
            "why_relevant": description[:150] if description else title[:150],
        })

    return items
