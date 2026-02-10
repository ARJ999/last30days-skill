"""Video search via Perplexity sonar-pro-search + sonar-deep-research through OpenRouter.

Two complementary calls:
- sonar-pro-search: Structured video items with URLs, creators, dates
- sonar-deep-research (deep mode): Comprehensive video discovery with richer context
"""

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

VIDEO_SEARCH_PROMPT = """Search for recent videos about: {topic}

Find {min_items}-{max_items} videos from the last 30 days on YouTube, Vimeo, and other video platforms.

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "title": "Video title",
      "url": "https://youtube.com/watch?v=...",
      "creator": "Channel or creator name",
      "date": "YYYY-MM-DD",
      "duration": "12:34",
      "snippet": "Brief description of the video content",
      "relevance": 0.85,
      "why_relevant": "Brief explanation of relevance"
    }}
  ]
}}

Rules:
- date must be YYYY-MM-DD format or null
- relevance is 0.0 to 1.0
- duration in MM:SS or HH:MM:SS format, or null if unknown
- creator is the channel/uploader name
- Include educational, tutorial, review, and informative content
- Prefer videos with high production quality and substantive content"""

# Deep research prompt for comprehensive video discovery
VIDEO_DEEP_RESEARCH_PROMPT = """Research the most important and talked-about videos about: {topic}

Search YouTube, Vimeo, and video platforms for the best video content from the last 30 days.
Identify:
1. The most-watched and most-shared videos on this topic
2. Notable creator/channel coverage (tutorials, deep-dives, reviews, explainers)
3. Conference talks, demos, or official announcements in video form
4. Community-recommended video resources

For each video found, provide the full URL, creator/channel name, and why it matters.
Include inline source citations [1], [2], etc."""


def _log(msg: str):
    sys.stderr.write(f"[PERPLEXITY-VIDEO] {msg}\n")
    sys.stderr.flush()


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def search_videos(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search for videos via Perplexity sonar-pro-search."""
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 60 if depth == "quick" else 90 if depth == "default" else 120

    response = client.chat(
        model=openrouter_client.SONAR_PRO_SEARCH,
        messages=[
            {"role": "system", "content": "You are a video research assistant. Return only valid JSON."},
            {"role": "user", "content": VIDEO_SEARCH_PROMPT.format(
                topic=topic, min_items=min_items, max_items=max_items,
            )},
        ],
        max_tokens=4096,
        temperature=0.3,
        search_domain_filter=["youtube.com", "vimeo.com", "dailymotion.com"],
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        search_context_size="high",
        timeout=timeout,
    )

    return response


def search_videos_deep(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run deep research for video discovery via sonar-deep-research.

    Only used in deep mode for richer video discovery with comprehensive context.

    Returns:
        Full OpenRouter response with video-focused research synthesis.
    """
    if mock_response is not None:
        return mock_response

    after_date = openrouter_client.format_date_filter(from_date)
    before_date = openrouter_client.format_date_filter(to_date)

    timeout = 120 if depth == "quick" else 180 if depth == "default" else 300

    response = client.chat(
        model=openrouter_client.SONAR_DEEP_RESEARCH,
        messages=[
            {"role": "user", "content": VIDEO_DEEP_RESEARCH_PROMPT.format(topic=topic)},
        ],
        max_tokens=4096,
        temperature=0.3,
        search_domain_filter=["youtube.com", "vimeo.com", "dailymotion.com"],
        search_recency_filter="month",
        search_after_date_filter=after_date,
        search_before_date_filter=before_date,
        return_related_questions=False,
        timeout=timeout,
    )

    return response


def parse_video_deep_research(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse deep research response to extract supplementary video items from citations.

    Returns:
        List of video item dicts discovered via deep research citations.
    """
    items = []

    annotations = openrouter_client.extract_annotations(response)
    citation_urls = openrouter_client.extract_citations(response)

    video_domains = {"youtube.com", "youtu.be", "vimeo.com", "dailymotion.com"}

    # Build items from annotations (richer) or fallback to citation URLs
    sources = annotations if annotations else [{"url": u, "title": "", "snippet": ""} for u in citation_urls]
    seen_urls = set()

    for ann in sources:
        url = ann.get("url", "")
        domain = _extract_domain(url)
        if not url or url in seen_urls:
            continue
        if not any(d in domain for d in video_domains):
            continue
        seen_urls.add(url)

        items.append({
            "id": f"V{len(items)+1}",
            "title": ann.get("title", "")[:200],
            "url": url,
            "source_domain": domain,
            "creator": None,
            "thumbnail_url": None,
            "duration": None,
            "snippet": ann.get("snippet", "")[:300],
            "date": None,
            "relevance": max(0.3, 1.0 - (len(items) / 15) * 0.7),
            "why_relevant": ann.get("snippet", "")[:150],
        })

    return items


def parse_video_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Perplexity video response into item dicts."""
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

        items.append({
            "id": f"V{len(items)+1}",
            "title": str(item.get("title", "")).strip()[:200],
            "url": url,
            "source_domain": _extract_domain(url),
            "creator": item.get("creator"),
            "thumbnail_url": None,
            "duration": item.get("duration"),
            "snippet": str(item.get("snippet", ""))[:300],
            "date": item.get("date"),
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
            "why_relevant": str(item.get("why_relevant", ""))[:150],
        })

    # Supplement from annotations (video platform URLs only)
    existing_urls = {item["url"] for item in items}
    video_domains = {"youtube.com", "youtu.be", "vimeo.com", "dailymotion.com"}
    for ann in annotations:
        url = ann.get("url", "")
        domain = _extract_domain(url)
        if url and url not in existing_urls and any(d in domain for d in video_domains):
            items.append({
                "id": f"V{len(items)+1}",
                "title": ann.get("title", "")[:200],
                "url": url,
                "source_domain": domain,
                "creator": None,
                "thumbnail_url": None,
                "duration": None,
                "snippet": ann.get("snippet", "")[:300],
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
