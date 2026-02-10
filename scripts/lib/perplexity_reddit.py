"""Reddit search via Perplexity sonar-pro-search through OpenRouter."""

import json
import re
import sys
from typing import Any, Dict, List, Optional

from . import openrouter_client

DEPTH_CONFIG = {
    "quick": (8, 12),
    "default": (15, 25),
    "deep": (25, 40),
}

REDDIT_SEARCH_PROMPT = """Search Reddit for threads and discussions about: {topic}

Find {min_items}-{max_items} Reddit threads from the last 30 days with substantive discussion.

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "title": "Thread title",
      "url": "https://www.reddit.com/r/subreddit/comments/...",
      "subreddit": "subreddit_name",
      "date": "YYYY-MM-DD",
      "snippet": "Brief description of the thread content and key discussion points",
      "relevance": 0.85,
      "why_relevant": "Brief explanation of relevance to the topic"
    }}
  ]
}}

Rules:
- Only include actual Reddit thread URLs (with /comments/ in the path)
- date must be YYYY-MM-DD format or null
- relevance is 0.0 to 1.0 (1.0 = highly relevant)
- Include diverse subreddits when applicable
- Prefer threads with substantive discussion, not just link posts
- Include the most upvoted and discussed threads first"""


def _log(msg: str):
    sys.stderr.write(f"[PERPLEXITY-REDDIT] {msg}\n")
    sys.stderr.flush()


def _extract_subreddit(url: str) -> str:
    """Extract subreddit from Reddit URL."""
    match = re.search(r'reddit\.com/r/([^/]+)', url)
    return match.group(1) if match else "unknown"


def _is_reddit_thread(url: str) -> bool:
    """Check if URL is a Reddit thread."""
    return bool(re.search(r'reddit\.com/r/[^/]+/comments/', url))


def search_reddit(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search for Reddit threads via Perplexity sonar-pro-search."""
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 60 if depth == "quick" else 90 if depth == "default" else 120

    response = client.chat(
        model=openrouter_client.SONAR_PRO_SEARCH,
        messages=[
            {"role": "system", "content": "You are a Reddit research assistant. Return only valid JSON."},
            {"role": "user", "content": REDDIT_SEARCH_PROMPT.format(
                topic=topic, min_items=min_items, max_items=max_items,
            )},
        ],
        max_tokens=4096,
        temperature=0.3,
        search_domain_filter=["reddit.com"],
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        search_context_size="high",
        timeout=timeout,
    )

    return response


def parse_reddit_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Perplexity Reddit response into item dicts for enrichment."""
    items = []

    content = openrouter_client.extract_content(response)
    if not content:
        return items

    # Parse JSON from response
    json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', content)
    if json_match:
        try:
            data = json.loads(json_match.group())
            raw_items = data.get("items", [])
        except json.JSONDecodeError:
            raw_items = []
    else:
        raw_items = []

    # Also get citation URLs as supplementary data
    annotations = openrouter_client.extract_annotations(response)

    # Process items from JSON
    for i, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if not url or "reddit.com" not in url:
            continue
        if not _is_reddit_thread(url):
            continue

        items.append({
            "id": f"R{len(items)+1}",
            "title": str(item.get("title", "")).strip()[:200],
            "url": url,
            "subreddit": item.get("subreddit") or _extract_subreddit(url),
            "date": item.get("date"),
            "engagement": None,  # Will be filled by reddit_enrich
            "engagement_verified": False,
            "snippet": str(item.get("snippet", ""))[:300],
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
            "why_relevant": str(item.get("why_relevant", ""))[:150],
        })

    # Add Reddit thread URLs from annotations not already in items
    existing_urls = {item["url"] for item in items}
    for ann in annotations:
        url = ann.get("url", "")
        if url and "reddit.com" in url and _is_reddit_thread(url) and url not in existing_urls:
            items.append({
                "id": f"R{len(items)+1}",
                "title": ann.get("title", "")[:200],
                "url": url,
                "subreddit": _extract_subreddit(url),
                "date": None,
                "engagement": None,
                "engagement_verified": False,
                "snippet": ann.get("snippet", "")[:300],
                "relevance": 0.5,
                "why_relevant": ann.get("snippet", "")[:150],
            })
            existing_urls.add(url)

    # Validate dates
    for item in items:
        if item["date"] and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"])):
            item["date"] = None

    return items
