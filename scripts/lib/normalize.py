"""Normalization of raw API data to canonical schema."""

from typing import Any, Dict, List, Union

from . import dates, schema

AnyItem = Union[
    schema.RedditItem, schema.XItem, schema.HNItem,
    schema.NewsItem, schema.WebItem, schema.VideoItem, schema.DiscussionItem,
]


def filter_by_date_range(
    items: List[AnyItem],
    from_date: str,
    to_date: str,
    require_date: bool = False,
) -> List[AnyItem]:
    """Hard filter: Remove items outside the date range.

    Defense-in-depth safety net. Perplexity's recency filter is the primary filter.
    """
    result = []
    for item in items:
        if item.date is None:
            if not require_date:
                result.append(item)
            continue
        if item.date < from_date:
            continue
        if item.date > to_date:
            continue
        result.append(item)
    return result


def normalize_reddit_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.RedditItem]:
    """Normalize raw Reddit items to schema."""
    normalized = []
    for item in items:
        engagement = None
        eng_raw = item.get("engagement")
        if isinstance(eng_raw, dict):
            engagement = schema.Engagement(
                score=eng_raw.get("score"),
                num_comments=eng_raw.get("num_comments"),
                upvote_ratio=eng_raw.get("upvote_ratio"),
            )
        top_comments = []
        for c in item.get("top_comments", []):
            top_comments.append(schema.Comment(
                score=c.get("score", 0), date=c.get("date"),
                author=c.get("author", ""), excerpt=c.get("excerpt", ""),
                url=c.get("url", ""),
            ))
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        normalized.append(schema.RedditItem(
            id=item.get("id", ""), title=item.get("title", ""),
            url=item.get("url", ""), subreddit=item.get("subreddit", ""),
            date=date_str, date_confidence=date_confidence,
            engagement=engagement,
            engagement_verified=item.get("engagement_verified", False),
            top_comments=top_comments,
            comment_insights=item.get("comment_insights", []),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def normalize_x_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.XItem]:
    """Normalize raw X items to schema."""
    normalized = []
    for item in items:
        engagement = None
        eng_raw = item.get("engagement")
        if isinstance(eng_raw, dict):
            engagement = schema.Engagement(
                likes=eng_raw.get("likes"), reposts=eng_raw.get("reposts"),
                replies=eng_raw.get("replies"), quotes=eng_raw.get("quotes"),
                views=eng_raw.get("views"), bookmarks=eng_raw.get("bookmarks"),
            )
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        engagement_verified = engagement is not None and (
            engagement.likes is not None or engagement.reposts is not None
        )
        normalized.append(schema.XItem(
            id=item.get("id", ""), text=item.get("text", ""),
            url=item.get("url", ""), author_handle=item.get("author_handle", ""),
            date=date_str, date_confidence=date_confidence,
            engagement=engagement, engagement_verified=engagement_verified,
            has_media=bool(item.get("has_media", False)),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def normalize_hn_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.HNItem]:
    """Normalize raw HackerNews items to schema."""
    normalized = []
    for item in items:
        engagement = None
        eng_raw = item.get("engagement")
        if isinstance(eng_raw, dict):
            engagement = schema.Engagement(
                points=eng_raw.get("points"),
                num_comments=eng_raw.get("num_comments"),
            )
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        normalized.append(schema.HNItem(
            id=item.get("id", ""), title=item.get("title", ""),
            url=item.get("url", ""), hn_url=item.get("hn_url", ""),
            author=item.get("author", ""),
            date=date_str, date_confidence=date_confidence,
            engagement=engagement, engagement_verified=True,
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def normalize_news_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.NewsItem]:
    """Normalize raw Perplexity News items to schema."""
    normalized = []
    for item in items:
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        if date_str and date_confidence == "low":
            date_confidence = "high"  # Trust Perplexity's date extraction
        normalized.append(schema.NewsItem(
            id=item.get("id", ""), title=item.get("title", ""),
            url=item.get("url", ""),
            source_name=item.get("source_name", ""),
            source_domain=item.get("source_domain", ""),
            date=date_str, date_confidence=date_confidence,
            snippet=item.get("snippet", ""),
            extra_snippets=item.get("extra_snippets", []),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def normalize_web_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.WebItem]:
    """Normalize raw Perplexity Web items to schema."""
    normalized = []
    for item in items:
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        if date_str and date_confidence == "low":
            date_confidence = "high"
        normalized.append(schema.WebItem(
            id=item.get("id", ""), title=item.get("title", ""),
            url=item.get("url", ""),
            source_domain=item.get("source_domain", ""),
            snippet=item.get("snippet", ""),
            extra_snippets=item.get("extra_snippets", []),
            date=date_str, date_confidence=date_confidence,
            has_schema_data=item.get("has_schema_data", False),
            schema_data=item.get("schema_data"),
            deep_results=item.get("deep_results"),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def normalize_video_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.VideoItem]:
    """Normalize raw Perplexity Video items to schema."""
    normalized = []
    for item in items:
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        if date_str and date_confidence == "low":
            date_confidence = "high"
        normalized.append(schema.VideoItem(
            id=item.get("id", ""), title=item.get("title", ""),
            url=item.get("url", ""),
            source_domain=item.get("source_domain", ""),
            creator=item.get("creator"), date=date_str,
            date_confidence=date_confidence,
            thumbnail_url=item.get("thumbnail_url"),
            duration=item.get("duration"),
            snippet=item.get("snippet", ""),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def normalize_discussion_items(
    items: List[Dict[str, Any]], from_date: str, to_date: str,
) -> List[schema.DiscussionItem]:
    """Normalize raw Perplexity Discussion items to schema."""
    normalized = []
    for item in items:
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)
        if date_str and date_confidence == "low":
            date_confidence = "high"
        normalized.append(schema.DiscussionItem(
            id=item.get("id", ""), title=item.get("title", ""),
            url=item.get("url", ""), forum_name=item.get("forum_name", ""),
            date=date_str, date_confidence=date_confidence,
            snippet=item.get("snippet", ""),
            extra_snippets=item.get("extra_snippets", []),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))
    return normalized


def items_to_dicts(items: List) -> List[Dict[str, Any]]:
    """Convert schema items to dicts for JSON serialization."""
    return [item.to_dict() for item in items]
