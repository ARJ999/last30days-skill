"""News search via Perplexity sonar-pro-search through OpenRouter."""

import json
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import openrouter_client

DEPTH_CONFIG = {
    "quick": (10, 15),
    "default": (15, 25),
    "deep": (25, 40),
}

NEWS_SEARCH_PROMPT = """Search for recent news articles about: {topic}

Find {min_items}-{max_items} news articles from the last 30 days from reputable news sources.

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "title": "Article headline",
      "url": "https://news-source.com/article...",
      "source_name": "Publication Name",
      "date": "YYYY-MM-DD",
      "snippet": "Brief summary of the article content",
      "relevance": 0.85,
      "why_relevant": "Brief explanation of relevance"
    }}
  ]
}}

Rules:
- date must be YYYY-MM-DD format or null
- relevance is 0.0 to 1.0
- Prefer reputable news sources (Reuters, AP, BBC, NYT, TechCrunch, The Verge, Ars Technica, etc.)
- Include diverse sources for balanced coverage
- Focus on the most significant and newsworthy articles
- Exclude social media posts (Reddit, Twitter, YouTube)"""


def _log(msg: str):
    sys.stderr.write(f"[PERPLEXITY-NEWS] {msg}\n")
    sys.stderr.flush()


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def search_news(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search for news articles via Perplexity sonar-pro-search."""
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 60 if depth == "quick" else 90 if depth == "default" else 120

    response = client.chat(
        model=openrouter_client.SONAR_PRO_SEARCH,
        messages=[
            {"role": "system", "content": "You are a news research assistant. Return only valid JSON."},
            {"role": "user", "content": NEWS_SEARCH_PROMPT.format(
                topic=topic, min_items=min_items, max_items=max_items,
            )},
        ],
        max_tokens=4096,
        temperature=0.3,
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        search_context_size="high",
        timeout=timeout,
    )

    return response


def parse_news_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Perplexity news response into item dicts."""
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

    # Social media domains to skip
    social_domains = {"reddit.com", "twitter.com", "x.com", "youtube.com"}

    for i, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if not url:
            continue

        domain = _extract_domain(url)
        if any(d in domain for d in social_domains):
            continue

        items.append({
            "id": f"N{len(items)+1}",
            "title": str(item.get("title", "")).strip()[:200],
            "url": url,
            "source_name": str(item.get("source_name", ""))[:100] or domain,
            "source_domain": domain,
            "snippet": str(item.get("snippet", ""))[:300],
            "extra_snippets": [],
            "date": item.get("date"),
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
            "why_relevant": str(item.get("why_relevant", ""))[:150],
        })

    # Add news-like URLs from annotations not already in items
    existing_urls = {item["url"] for item in items}
    for ann in annotations:
        url = ann.get("url", "")
        domain = _extract_domain(url)
        if url and url not in existing_urls:
            if any(d in domain for d in social_domains):
                continue
            items.append({
                "id": f"N{len(items)+1}",
                "title": ann.get("title", "")[:200],
                "url": url,
                "source_name": domain,
                "source_domain": domain,
                "snippet": ann.get("snippet", "")[:300],
                "extra_snippets": [],
                "date": None,
                "relevance": 0.4,
                "why_relevant": ann.get("snippet", "")[:150],
            })
            existing_urls.add(url)

    # Validate dates
    for item in items:
        if item["date"] and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"])):
            item["date"] = None

    return items
