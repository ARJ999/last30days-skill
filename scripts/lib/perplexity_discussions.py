"""Discussion/forum search via Perplexity sonar-pro-search through OpenRouter."""

import json
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import openrouter_client

DEPTH_CONFIG = {
    "quick": (5, 10),
    "default": (10, 20),
    "deep": (15, 30),
}

DISCUSSIONS_SEARCH_PROMPT = """Search for forum discussions and Q&A threads about: {topic}

Find {min_items}-{max_items} discussion threads from the last 30 days on technical forums,
Q&A sites, and community platforms (Stack Overflow, Stack Exchange, Discourse forums, etc.).

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "title": "Discussion title or question",
      "url": "https://stackoverflow.com/questions/...",
      "forum_name": "Stack Overflow",
      "date": "YYYY-MM-DD",
      "snippet": "Brief description of the discussion or top answer",
      "relevance": 0.85,
      "why_relevant": "Brief explanation of relevance"
    }}
  ]
}}

Rules:
- date must be YYYY-MM-DD format or null
- relevance is 0.0 to 1.0
- forum_name is the platform name (e.g. "Stack Overflow", "Dev.to", "Discourse")
- Exclude Reddit threads (those are covered by another source)
- Include Stack Overflow, Stack Exchange, Discourse forums, Dev.to discussions
- Prefer threads with accepted answers or significant engagement"""


def _log(msg: str):
    sys.stderr.write(f"[PERPLEXITY-DISCUSSIONS] {msg}\n")
    sys.stderr.flush()


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def _extract_forum_name(url: str) -> str:
    """Derive forum name from URL domain."""
    domain = _extract_domain(url)
    known = {
        "stackoverflow.com": "Stack Overflow",
        "stackexchange.com": "Stack Exchange",
        "superuser.com": "Super User",
        "serverfault.com": "Server Fault",
        "askubuntu.com": "Ask Ubuntu",
        "dev.to": "Dev.to",
        "discourse.org": "Discourse",
        "community.cloudflare.com": "Cloudflare Community",
        "discuss.python.org": "Python Discuss",
        "forum.unity.com": "Unity Forums",
        "forums.docker.com": "Docker Forums",
    }
    for pattern, name in known.items():
        if pattern in domain:
            return name
    return domain


def search_discussions(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search for forum discussions via Perplexity sonar-pro-search."""
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 60 if depth == "quick" else 90 if depth == "default" else 120

    # Target forum/Q&A domains
    forum_domains = [
        "stackoverflow.com", "stackexchange.com", "superuser.com",
        "serverfault.com", "askubuntu.com", "dev.to",
        "discourse.org", "community.cloudflare.com",
    ]

    response = client.chat(
        model=openrouter_client.SONAR_PRO_SEARCH,
        messages=[
            {"role": "system", "content": "You are a forum research assistant. Return only valid JSON."},
            {"role": "user", "content": DISCUSSIONS_SEARCH_PROMPT.format(
                topic=topic, min_items=min_items, max_items=max_items,
            )},
        ],
        max_tokens=4096,
        temperature=0.3,
        search_domain_filter=forum_domains,
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        search_context_size="high",
        timeout=timeout,
    )

    return response


def parse_discussion_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Perplexity discussion response into item dicts."""
    items = []

    content = openrouter_client.extract_content(response)
    if not content:
        return items

    json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', content)
    if json_match:
        try:
            data = json.loads(json_match.group())
            raw_items = data.get("items", [])
        except json.JSONDecodeError:
            raw_items = []
    else:
        raw_items = []

    annotations = openrouter_client.extract_annotations(response)

    # Domains to exclude
    excluded = {"reddit.com", "twitter.com", "x.com", "youtube.com"}

    for i, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if not url:
            continue

        domain = _extract_domain(url)
        if any(d in domain for d in excluded):
            continue

        items.append({
            "id": f"D{len(items)+1}",
            "title": str(item.get("title", "")).strip()[:200],
            "url": url,
            "forum_name": item.get("forum_name") or _extract_forum_name(url),
            "date": item.get("date"),
            "snippet": str(item.get("snippet", ""))[:300],
            "extra_snippets": [],
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
            "why_relevant": str(item.get("why_relevant", ""))[:150],
        })

    # Supplement from annotations
    existing_urls = {item["url"] for item in items}
    for ann in annotations:
        url = ann.get("url", "")
        domain = _extract_domain(url)
        if url and url not in existing_urls:
            if any(d in domain for d in excluded):
                continue
            items.append({
                "id": f"D{len(items)+1}",
                "title": ann.get("title", "")[:200],
                "url": url,
                "forum_name": _extract_forum_name(url),
                "date": None,
                "snippet": ann.get("snippet", "")[:300],
                "extra_snippets": [],
                "relevance": 0.4,
                "why_relevant": ann.get("snippet", "")[:150],
            })
            existing_urls.add(url)

    # Validate dates
    for item in items:
        if item["date"] and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"])):
            item["date"] = None

    return items
