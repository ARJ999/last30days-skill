"""Web research via Perplexity sonar-deep-research + sonar-pro-search through OpenRouter.

Two complementary calls:
- sonar-deep-research: Comprehensive AI summary with citations and follow-ups
- sonar-pro-search: Structured web result items with dates and relevance
"""

import json
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import openrouter_client

DEPTH_CONFIG = {
    "quick": (8, 12),
    "default": (12, 20),
    "deep": (20, 35),
}

# Deep research prompt (comprehensive synthesis)
DEEP_RESEARCH_PROMPT = """Conduct comprehensive research on: {topic}

Research this topic thoroughly using web sources from the last 30 days. Provide:
1. A detailed research synthesis covering key findings, trends, and insights
2. What the community and industry are saying about this topic
3. Key developments, announcements, or changes
4. Notable opinions, recommendations, and best practices

Focus on the most authoritative and recent sources. Be specific with facts, names, and details.
Include inline source citations [1], [2], etc."""

# Structured web items prompt (for sonar-pro-search)
WEB_ITEMS_PROMPT = """Search the web for pages, articles, tutorials, and resources about: {topic}

Find {min_items}-{max_items} high-quality web pages from the last 30 days.

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "title": "Page title",
      "url": "https://example.com/...",
      "date": "YYYY-MM-DD",
      "snippet": "Brief description of the page content and key information",
      "relevance": 0.85,
      "why_relevant": "Brief explanation of relevance"
    }}
  ]
}}

Rules:
- date must be YYYY-MM-DD format or null
- relevance is 0.0 to 1.0
- Exclude Reddit, Twitter/X, HackerNews URLs (those are covered by other sources)
- Include blogs, documentation, tutorials, official announcements, tech publications
- Prefer authoritative and recently updated sources
- Include diverse domains for broad coverage"""

# Social media domains to exclude from web results
EXCLUDED_DOMAINS = {"reddit.com", "twitter.com", "x.com", "news.ycombinator.com"}


def _log(msg: str):
    sys.stderr.write(f"[PERPLEXITY-WEB] {msg}\n")
    sys.stderr.flush()


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def search_web_deep(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run deep research via sonar-deep-research for AI summary + citations.

    Returns:
        Full OpenRouter response with comprehensive research synthesis.
    """
    if mock_response is not None:
        return mock_response

    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 120 if depth == "quick" else 180 if depth == "default" else 300

    response = client.chat(
        model=openrouter_client.SONAR_DEEP_RESEARCH,
        messages=[
            {"role": "user", "content": DEEP_RESEARCH_PROMPT.format(topic=topic)},
        ],
        max_tokens=8000,
        temperature=0.3,
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        return_related_questions=True,
        timeout=timeout,
    )

    return response


def search_web_items(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search for structured web results via sonar-pro-search.

    Returns:
        Full OpenRouter response with structured web items.
    """
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 60 if depth == "quick" else 90 if depth == "default" else 120

    # Exclude domains covered by other sources
    exclude_domains = [f"-{d}" for d in EXCLUDED_DOMAINS]

    response = client.chat(
        model=openrouter_client.SONAR_PRO_SEARCH,
        messages=[
            {"role": "system", "content": "You are a web research assistant. Return only valid JSON."},
            {"role": "user", "content": WEB_ITEMS_PROMPT.format(
                topic=topic, min_items=min_items, max_items=max_items,
            )},
        ],
        max_tokens=4096,
        temperature=0.3,
        search_domain_filter=exclude_domains,
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        search_context_size="high",
        timeout=timeout,
    )

    return response


def parse_deep_research(response: Dict[str, Any]) -> Dict[str, Any]:
    """Parse deep research response for AI summary, citations, and follow-ups.

    Returns:
        Dict with summary, citations, followups, and web_items from citations.
    """
    result = {
        "summary": None,
        "citations": [],
        "followups": [],
        "web_items": [],
    }

    # The response content IS the research summary
    content = openrouter_client.extract_content(response)
    if content:
        result["summary"] = content

    # Extract citations from annotations (richer) and top-level citations
    annotations = openrouter_client.extract_annotations(response)
    citation_urls = openrouter_client.extract_citations(response)

    # Build citations list
    if annotations:
        for i, ann in enumerate(annotations):
            result["citations"].append({
                "number": i + 1,
                "url": ann.get("url", ""),
                "title": ann.get("title", ""),
            })
    elif citation_urls:
        for i, url in enumerate(citation_urls):
            result["citations"].append({
                "number": i + 1,
                "url": url,
                "title": "",
            })

    # Build web items from citations (supplementary to sonar-pro-search items)
    seen_urls = set()
    sources = annotations if annotations else [{"url": u, "title": "", "snippet": ""} for u in citation_urls]
    for ann in sources:
        url = ann.get("url", "")
        domain = _extract_domain(url)
        if not url or url in seen_urls:
            continue
        if any(d in domain for d in EXCLUDED_DOMAINS):
            continue
        seen_urls.add(url)
        result["web_items"].append({
            "id": f"W{len(result['web_items'])+1}",
            "title": ann.get("title", "")[:200],
            "url": url,
            "source_domain": domain,
            "snippet": ann.get("snippet", "")[:300],
            "extra_snippets": [],
            "date": None,
            "relevance": max(0.3, 1.0 - (len(result["web_items"]) / 20) * 0.7),
            "why_relevant": ann.get("snippet", "")[:150],
        })

    # Extract follow-up questions (Perplexity return_related_questions)
    related = response.get("related_questions", [])
    if isinstance(related, list):
        result["followups"] = [str(q) for q in related if q]

    return result


def parse_web_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse sonar-pro-search web response into item dicts."""
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

    for i, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if not url:
            continue

        domain = _extract_domain(url)
        if any(d in domain for d in EXCLUDED_DOMAINS):
            continue

        items.append({
            "id": f"W{len(items)+1}",
            "title": str(item.get("title", "")).strip()[:200],
            "url": url,
            "source_domain": domain,
            "snippet": str(item.get("snippet", ""))[:300],
            "extra_snippets": [],
            "date": item.get("date"),
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
            "why_relevant": str(item.get("why_relevant", ""))[:150],
        })

    # Supplement from annotations
    existing_urls = {item["url"] for item in items}
    for ann in annotations:
        url = ann.get("url", "")
        domain = _extract_domain(url)
        if url and url not in existing_urls:
            if any(d in domain for d in EXCLUDED_DOMAINS):
                continue
            items.append({
                "id": f"W{len(items)+1}",
                "title": ann.get("title", "")[:200],
                "url": url,
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


def parse_discussions(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract discussion-type items from web search response.

    Not used in the Perplexity architecture (discussions have their own module).
    Kept for backward compatibility with the orchestrator interface.
    """
    return []
