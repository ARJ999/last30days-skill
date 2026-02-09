"""Reddit discovery via Brave Web Search with site:reddit.com."""

import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import brave_client, dates

# Depth config: pages to fetch
DEPTH_PAGES = {
    "quick": 1,
    "default": 2,
    "deep": 3,
}


def _log(msg: str):
    sys.stderr.write(f"[BRAVE-REDDIT] {msg}\n")
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


def _extract_subreddit(url: str) -> str:
    """Extract subreddit name from Reddit URL."""
    match = re.search(r'reddit\.com/r/([^/]+)', url)
    if match:
        return match.group(1)
    return "unknown"


def _is_reddit_thread(url: str) -> bool:
    """Check if URL is a Reddit thread (not just subreddit or user page)."""
    return bool(re.search(r'reddit\.com/r/[^/]+/comments/', url))


def search_reddit(
    client: brave_client.BraveClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> Dict[str, Any]:
    """Search Brave for Reddit threads about the topic.

    Uses site:reddit.com operator to restrict results to Reddit.

    Returns:
        Dict with 'results' key containing raw Brave web results
    """
    freshness = f"{from_date}to{to_date}"
    pages = DEPTH_PAGES.get(depth, 2)

    all_results = []

    for page in range(pages):
        try:
            response = client.web_search(
                q=f"{topic} site:reddit.com",
                freshness=freshness,
                count=20,
                offset=page,
                extra_snippets=True,
                summary=False,
            )
        except brave_client.BraveError as e:
            _log(f"Page {page} error: {e}")
            if page == 0:
                raise
            break

        web = response.get("web", {})
        all_results.extend(web.get("results", []))

        if not response.get("query", {}).get("more_results_available", False):
            break

    # Retry with simplified query if few results
    if len(all_results) < 5:
        core_terms = _simplify_topic(topic)
        if core_terms != topic:
            try:
                response = client.web_search(
                    q=f"{core_terms} site:reddit.com",
                    freshness=freshness,
                    count=20,
                    offset=0,
                    extra_snippets=True,
                )
                web = response.get("web", {})
                existing_urls = {r.get("url") for r in all_results}
                for r in web.get("results", []):
                    if r.get("url") not in existing_urls:
                        all_results.append(r)
            except brave_client.BraveError:
                pass

    return {"results": all_results}


def _simplify_topic(topic: str) -> str:
    """Simplify topic to 2-3 core terms for broader matching."""
    words = topic.split()
    # Remove common filler words
    stop_words = {"the", "a", "an", "for", "to", "in", "on", "with", "and", "or", "is", "are", "best", "top", "how"}
    core = [w for w in words if w.lower() not in stop_words]
    if len(core) >= 2:
        return " ".join(core[:3])
    return topic


def parse_reddit_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Brave Reddit-focused results into item dicts for enrichment."""
    items = []
    results = response.get("results", [])

    total = len(results)
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            continue

        url = result.get("url", "")
        if not url or "reddit.com" not in url:
            continue

        # Prefer thread URLs over subreddit/user pages
        if not _is_reddit_thread(url):
            continue

        title = result.get("title", "").strip()
        # Clean Reddit title format: "Title : subreddit" -> "Title"
        if " : " in title:
            title = title.split(" : ")[0].strip()

        description = result.get("description", "").strip()
        page_age = _parse_page_age(result.get("page_age"))
        subreddit = _extract_subreddit(url)

        # Position-based relevance
        relevance = max(0.3, 1.0 - (i / max(total, 1)) * 0.7)

        items.append({
            "id": f"R{len(items)+1}",
            "title": title[:200],
            "url": url,
            "subreddit": subreddit,
            "date": page_age,
            "engagement": None,  # Will be filled by reddit_enrich
            "engagement_verified": False,
            "why_relevant": description[:150] if description else title[:150],
            "relevance": relevance,
        })

    return items
