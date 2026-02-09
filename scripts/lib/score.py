"""Popularity-aware scoring for last30days skill."""

import math
from typing import List, Optional, Union

from . import dates, schema

# Score weights for Reddit/X/HN (has engagement)
# Balanced for quality: relevance most important, then engagement (verified), then recency
WEIGHT_RELEVANCE = 0.40
WEIGHT_RECENCY = 0.25
WEIGHT_ENGAGEMENT = 0.35

# News weights (no engagement, time-sensitive)
NEWS_WEIGHT_RELEVANCE = 0.45
NEWS_WEIGHT_RECENCY = 0.55

# Web weights (no engagement, relevance-focused)
WEB_WEIGHT_RELEVANCE = 0.55
WEB_WEIGHT_RECENCY = 0.45
WEB_SOURCE_PENALTY = 10  # Points deducted for lacking engagement
WEB_SCHEMA_BONUS = 5     # Bonus for schema-enriched results
WEB_EXTRA_SNIPPETS_BONUS = 3  # Bonus for having extra snippets

# Video weights (no engagement, balanced)
VIDEO_WEIGHT_RELEVANCE = 0.50
VIDEO_WEIGHT_RECENCY = 0.50

# Discussion weights (engagement-like signals from forum context)
DISCUSSION_WEIGHT_RELEVANCE = 0.45
DISCUSSION_WEIGHT_RECENCY = 0.25
DISCUSSION_WEIGHT_ENGAGEMENT = 0.30

# Date confidence adjustments
HIGH_DATE_BONUS = 5       # Bonus for URL-verified recent date
NO_DATE_PENALTY = 20      # Heavy penalty for no date signals

# Default engagement score for unknown
DEFAULT_ENGAGEMENT = 20
UNKNOWN_ENGAGEMENT_PENALTY = 15

# Engagement verification bonus
VERIFIED_ENGAGEMENT_BONUS = 8


def log1p_safe(x: Optional[int]) -> float:
    """Safe log1p that handles None and negative values."""
    if x is None or x < 0:
        return 0.0
    return math.log1p(x)


def compute_reddit_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for Reddit item.

    Quality-focused formula prioritizing community agreement:
    - 45% upvote score (popularity)
    - 30% upvote ratio (community agreement - strong quality signal)
    - 25% comments (discussion depth)
    """
    if engagement is None:
        return None
    if engagement.score is None and engagement.num_comments is None:
        return None

    score_val = log1p_safe(engagement.score)
    comments = log1p_safe(engagement.num_comments)
    ratio = (engagement.upvote_ratio or 0.5) * 10

    return 0.45 * score_val + 0.30 * ratio + 0.25 * comments


def compute_x_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for X item.

    Quality-focused formula using all available X metrics:
    - 30% reposts (deep engagement - users amplify content they strongly endorse)
    - 25% likes (popularity/volume)
    - 20% views (reach/impression - normalized with log scale)
    - 10% replies (discussion, though can be negative)
    - 10% quotes (engagement with commentary)
    - 5% bookmarks (save intent - strong quality signal)
    """
    if engagement is None:
        return None
    if engagement.likes is None and engagement.reposts is None:
        return None

    likes = log1p_safe(engagement.likes)
    reposts = log1p_safe(engagement.reposts)
    replies = log1p_safe(engagement.replies)
    quotes = log1p_safe(engagement.quotes)
    views = log1p_safe(engagement.views)
    bookmarks = log1p_safe(engagement.bookmarks)

    return (0.30 * reposts + 0.25 * likes + 0.20 * views +
            0.10 * replies + 0.10 * quotes + 0.05 * bookmarks)


def compute_hn_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for HackerNews item.

    HN uses points (upvotes) and comments as engagement metrics.
    - 60% points (community upvotes - strong quality signal on HN)
    - 40% comments (discussion depth)
    """
    if engagement is None:
        return None
    if engagement.points is None and engagement.num_comments is None:
        return None

    points = log1p_safe(engagement.points)
    comments = log1p_safe(engagement.num_comments)

    return 0.60 * points + 0.40 * comments


def normalize_to_100(values: List[float], default: float = 50) -> List[float]:
    """Normalize a list of values to 0-100 scale."""
    valid = [v for v in values if v is not None]
    if not valid:
        return [default if v is None else 50 for v in values]

    min_val = min(valid)
    max_val = max(valid)
    range_val = max_val - min_val

    if range_val == 0:
        return [50 if v is None else 50 for v in values]

    result = []
    for v in values:
        if v is None:
            result.append(None)
        else:
            normalized = ((v - min_val) / range_val) * 100
            result.append(normalized)

    return result


def _apply_date_confidence(overall: float, date_confidence: str) -> float:
    """Apply date confidence adjustments to score."""
    if date_confidence == "high":
        overall += HIGH_DATE_BONUS
    elif date_confidence == "low":
        overall -= NO_DATE_PENALTY
    elif date_confidence == "med":
        overall -= 5
    return overall


def _score_with_engagement(
    items: list,
    compute_engagement_fn,
    weight_rel: float = WEIGHT_RELEVANCE,
    weight_rec: float = WEIGHT_RECENCY,
    weight_eng: float = WEIGHT_ENGAGEMENT,
) -> list:
    """Generic engagement-based scoring for Reddit/X/HN items."""
    if not items:
        return items

    eng_raw = [compute_engagement_fn(item.engagement) for item in items]
    eng_normalized = normalize_to_100(eng_raw)

    for i, item in enumerate(items):
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)

        if eng_normalized[i] is not None:
            eng_score = int(eng_normalized[i])
        else:
            eng_score = DEFAULT_ENGAGEMENT

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=eng_score,
        )

        overall = (
            weight_rel * rel_score +
            weight_rec * rec_score +
            weight_eng * eng_score
        )

        if item.engagement_verified:
            overall += VERIFIED_ENGAGEMENT_BONUS
        elif eng_raw[i] is None:
            overall -= UNKNOWN_ENGAGEMENT_PENALTY

        overall = _apply_date_confidence(overall, item.date_confidence)
        item.score = max(0, min(100, int(overall)))

    return items


def score_reddit_items(items: List[schema.RedditItem]) -> List[schema.RedditItem]:
    """Compute scores for Reddit items.

    Weights: 40% relevance + 25% recency + 35% engagement
    """
    return _score_with_engagement(items, compute_reddit_engagement_raw)


def score_x_items(items: List[schema.XItem]) -> List[schema.XItem]:
    """Compute scores for X items.

    Weights: 40% relevance + 25% recency + 35% engagement
    """
    return _score_with_engagement(items, compute_x_engagement_raw)


def score_hn_items(items: List[schema.HNItem]) -> List[schema.HNItem]:
    """Compute scores for HackerNews items.

    Weights: 40% relevance + 25% recency + 35% engagement
    """
    return _score_with_engagement(items, compute_hn_engagement_raw)


def score_news_items(items: List[schema.NewsItem]) -> List[schema.NewsItem]:
    """Compute scores for News items.

    Weights: 45% relevance + 55% recency (time-sensitive, no engagement data)
    News articles are time-critical so recency gets higher weight.
    """
    if not items:
        return items

    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=0,
        )

        overall = (
            NEWS_WEIGHT_RELEVANCE * rel_score +
            NEWS_WEIGHT_RECENCY * rec_score
        )

        overall = _apply_date_confidence(overall, item.date_confidence)
        item.score = max(0, min(100, int(overall)))

    return items


def score_web_items(items: List[schema.WebItem]) -> List[schema.WebItem]:
    """Compute scores for Web items.

    Weights: 55% relevance + 45% recency - 10pt penalty + bonuses
    Web items lack engagement data, so they rank below Reddit/X/HN by default.
    Schema data and extra snippets provide small bonuses for richer results.
    """
    if not items:
        return items

    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=0,
        )

        overall = (
            WEB_WEIGHT_RELEVANCE * rel_score +
            WEB_WEIGHT_RECENCY * rec_score
        )

        # Source penalty (no engagement data)
        overall -= WEB_SOURCE_PENALTY

        # Schema data bonus (structured data = higher quality page)
        if item.has_schema_data:
            overall += WEB_SCHEMA_BONUS

        # Extra snippets bonus (more content = more relevant)
        if item.extra_snippets:
            overall += WEB_EXTRA_SNIPPETS_BONUS

        overall = _apply_date_confidence(overall, item.date_confidence)
        item.score = max(0, min(100, int(overall)))

    return items


def score_video_items(items: List[schema.VideoItem]) -> List[schema.VideoItem]:
    """Compute scores for Video items.

    Weights: 50% relevance + 50% recency (balanced, no engagement data)
    """
    if not items:
        return items

    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=0,
        )

        overall = (
            VIDEO_WEIGHT_RELEVANCE * rel_score +
            VIDEO_WEIGHT_RECENCY * rec_score
        )

        overall = _apply_date_confidence(overall, item.date_confidence)
        item.score = max(0, min(100, int(overall)))

    return items


def score_discussion_items(items: List[schema.DiscussionItem]) -> List[schema.DiscussionItem]:
    """Compute scores for Discussion items.

    Weights: 45% relevance + 25% recency + 30% engagement-proxy
    Discussions get an engagement-proxy score based on snippet richness
    (extra_snippets count as engagement signal since forums with more
    content indicate deeper discussion).
    """
    if not items:
        return items

    for item in items:
        rel_score = int(item.relevance * 100)
        rec_score = dates.recency_score(item.date)

        # Engagement proxy: extra_snippets count maps to engagement signal
        snippet_count = len(item.extra_snippets) if item.extra_snippets else 0
        eng_proxy = min(100, snippet_count * 20)  # 0-5 snippets -> 0-100

        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=eng_proxy,
        )

        overall = (
            DISCUSSION_WEIGHT_RELEVANCE * rel_score +
            DISCUSSION_WEIGHT_RECENCY * rec_score +
            DISCUSSION_WEIGHT_ENGAGEMENT * eng_proxy
        )

        overall = _apply_date_confidence(overall, item.date_confidence)
        item.score = max(0, min(100, int(overall)))

    return items


# Type union for all scoreable items
AnyItem = Union[
    schema.RedditItem, schema.XItem, schema.HNItem,
    schema.NewsItem, schema.WebItem, schema.VideoItem, schema.DiscussionItem,
]

# Source priority for sort tiebreaker (lower = higher priority)
SOURCE_PRIORITY = {
    schema.RedditItem: 0,
    schema.XItem: 1,
    schema.HNItem: 2,
    schema.NewsItem: 3,
    schema.DiscussionItem: 4,
    schema.WebItem: 5,
    schema.VideoItem: 6,
}


def sort_items(items: List[AnyItem]) -> List[AnyItem]:
    """Sort items by score (descending), then date, then source priority."""
    def sort_key(item):
        score = -item.score
        date = item.date or "0000-00-00"
        date_key = -int(date.replace("-", ""))
        source_priority = SOURCE_PRIORITY.get(type(item), 9)
        text = getattr(item, "title", "") or getattr(item, "text", "")
        return (score, date_key, source_priority, text)

    return sorted(items, key=sort_key)
