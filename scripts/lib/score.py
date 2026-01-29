"""Popularity-aware scoring for last30days skill."""

import math
from typing import List, Optional, Union

from . import dates, schema

# Score weights for Reddit/X (has engagement)
# Balanced for quality: relevance most important, then engagement (verified), then recency
WEIGHT_RELEVANCE = 0.40
WEIGHT_RECENCY = 0.25
WEIGHT_ENGAGEMENT = 0.35  # Increased - verified engagement is a strong quality signal

# WebSearch weights (no engagement, reweighted to 100%)
WEBSEARCH_WEIGHT_RELEVANCE = 0.55
WEBSEARCH_WEIGHT_RECENCY = 0.45
WEBSEARCH_SOURCE_PENALTY = 15  # Points deducted for lacking engagement

# WebSearch date confidence adjustments
WEBSEARCH_VERIFIED_BONUS = 10   # Bonus for URL-verified recent date (high confidence)
WEBSEARCH_NO_DATE_PENALTY = 20  # Heavy penalty for no date signals (low confidence)

# Default engagement score for unknown - lowered to not compete with verified data
DEFAULT_ENGAGEMENT = 20  # Reduced from 35 - unverified should rank lower
UNKNOWN_ENGAGEMENT_PENALTY = 15  # Increased from 10 - stronger penalty for unverified

# Engagement verification bonus
VERIFIED_ENGAGEMENT_BONUS = 8  # Bonus for items with verified real engagement data


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

    Formula: 0.45*log1p(score) + 0.30*(upvote_ratio*10) + 0.25*log1p(num_comments)
    """
    if engagement is None:
        return None

    if engagement.score is None and engagement.num_comments is None:
        return None

    score_val = log1p_safe(engagement.score)
    comments = log1p_safe(engagement.num_comments)
    # upvote_ratio is 0-1, scale to 0-10 for comparable weight
    # High ratio (>0.9) indicates strong community agreement
    ratio = (engagement.upvote_ratio or 0.5) * 10

    return 0.45 * score_val + 0.30 * ratio + 0.25 * comments


def compute_x_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for X item.

    Quality-focused formula prioritizing deep engagement:
    - 40% reposts (deep engagement - users amplify content they strongly endorse)
    - 35% likes (popularity/volume)
    - 15% replies (discussion, though can be negative)
    - 10% quotes (engagement with commentary)

    Formula: 0.40*log1p(reposts) + 0.35*log1p(likes) + 0.15*log1p(replies) + 0.10*log1p(quotes)
    """
    if engagement is None:
        return None

    if engagement.likes is None and engagement.reposts is None:
        return None

    likes = log1p_safe(engagement.likes)
    reposts = log1p_safe(engagement.reposts)
    replies = log1p_safe(engagement.replies)
    quotes = log1p_safe(engagement.quotes)

    return 0.40 * reposts + 0.35 * likes + 0.15 * replies + 0.10 * quotes


def normalize_to_100(values: List[float], default: float = 50) -> List[float]:
    """Normalize a list of values to 0-100 scale.

    Args:
        values: Raw values (None values are preserved)
        default: Default value for None entries

    Returns:
        Normalized values
    """
    # Filter out None
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


def score_reddit_items(items: List[schema.RedditItem]) -> List[schema.RedditItem]:
    """Compute scores for Reddit items.

    Quality-focused scoring that rewards:
    - High relevance to topic
    - Fresh/recent content (exponential bias)
    - Verified engagement data (real upvotes/comments)
    - High upvote ratio (community agreement)

    Args:
        items: List of Reddit items

    Returns:
        Items with updated scores
    """
    if not items:
        return items

    # Compute raw engagement scores
    eng_raw = [compute_reddit_engagement_raw(item.engagement) for item in items]

    # Normalize engagement to 0-100
    eng_normalized = normalize_to_100(eng_raw)

    for i, item in enumerate(items):
        # Relevance subscore (model-provided, convert to 0-100)
        rel_score = int(item.relevance * 100)

        # Recency subscore (uses exponential freshness bias)
        rec_score = dates.recency_score(item.date)

        # Engagement subscore
        if eng_normalized[i] is not None:
            eng_score = int(eng_normalized[i])
        else:
            eng_score = DEFAULT_ENGAGEMENT

        # Store subscores
        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=eng_score,
        )

        # Compute overall score
        overall = (
            WEIGHT_RELEVANCE * rel_score +
            WEIGHT_RECENCY * rec_score +
            WEIGHT_ENGAGEMENT * eng_score
        )

        # Apply bonus for verified engagement (real data from Reddit JSON)
        if item.engagement_verified:
            overall += VERIFIED_ENGAGEMENT_BONUS
        elif eng_raw[i] is None:
            # Apply penalty for unknown engagement
            overall -= UNKNOWN_ENGAGEMENT_PENALTY

        # Apply penalty for low date confidence
        if item.date_confidence == "low":
            overall -= 10
        elif item.date_confidence == "med":
            overall -= 5

        item.score = max(0, min(100, int(overall)))

    return items


def score_x_items(items: List[schema.XItem]) -> List[schema.XItem]:
    """Compute scores for X items.

    Quality-focused scoring that rewards:
    - High relevance to topic
    - Fresh/recent content (exponential bias)
    - Verified engagement data (real likes/reposts)
    - High repost ratio (deep engagement signal)

    Args:
        items: List of X items

    Returns:
        Items with updated scores
    """
    if not items:
        return items

    # Compute raw engagement scores
    eng_raw = [compute_x_engagement_raw(item.engagement) for item in items]

    # Normalize engagement to 0-100
    eng_normalized = normalize_to_100(eng_raw)

    for i, item in enumerate(items):
        # Relevance subscore (model-provided, convert to 0-100)
        rel_score = int(item.relevance * 100)

        # Recency subscore (uses exponential freshness bias)
        rec_score = dates.recency_score(item.date)

        # Engagement subscore
        if eng_normalized[i] is not None:
            eng_score = int(eng_normalized[i])
        else:
            eng_score = DEFAULT_ENGAGEMENT

        # Store subscores
        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=eng_score,
        )

        # Compute overall score
        overall = (
            WEIGHT_RELEVANCE * rel_score +
            WEIGHT_RECENCY * rec_score +
            WEIGHT_ENGAGEMENT * eng_score
        )

        # Apply bonus for verified engagement (real data from X API)
        if item.engagement_verified:
            overall += VERIFIED_ENGAGEMENT_BONUS
        elif eng_raw[i] is None:
            # Apply penalty for unknown engagement
            overall -= UNKNOWN_ENGAGEMENT_PENALTY

        # Apply penalty for low date confidence
        if item.date_confidence == "low":
            overall -= 10
        elif item.date_confidence == "med":
            overall -= 5

        item.score = max(0, min(100, int(overall)))

    return items


def compute_hn_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for HackerNews item.

    HN uses points (upvotes) and comments as engagement metrics.
    Quality-focused formula:
    - 60% points (community upvotes - strong quality signal on HN)
    - 40% comments (discussion depth)

    Formula: 0.60*log1p(points) + 0.40*log1p(num_comments)
    """
    if engagement is None:
        return None

    if engagement.points is None and engagement.num_comments is None:
        return None

    points = log1p_safe(engagement.points)
    comments = log1p_safe(engagement.num_comments)

    return 0.60 * points + 0.40 * comments


def score_hn_items(items: List[schema.HNItem]) -> List[schema.HNItem]:
    """Compute scores for HackerNews items.

    Quality-focused scoring for developer community insights:
    - High relevance to topic
    - Fresh/recent content (exponential bias)
    - Verified engagement data (points from HN API)
    - Discussion depth (comments)

    Args:
        items: List of HN items

    Returns:
        Items with updated scores
    """
    if not items:
        return items

    # Compute raw engagement scores
    eng_raw = [compute_hn_engagement_raw(item.engagement) for item in items]

    # Normalize engagement to 0-100
    eng_normalized = normalize_to_100(eng_raw)

    for i, item in enumerate(items):
        # Relevance subscore (search-ranking based, convert to 0-100)
        rel_score = int(item.relevance * 100)

        # Recency subscore (uses exponential freshness bias)
        rec_score = dates.recency_score(item.date)

        # Engagement subscore
        if eng_normalized[i] is not None:
            eng_score = int(eng_normalized[i])
        else:
            eng_score = DEFAULT_ENGAGEMENT

        # Store subscores
        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=eng_score,
        )

        # Compute overall score
        overall = (
            WEIGHT_RELEVANCE * rel_score +
            WEIGHT_RECENCY * rec_score +
            WEIGHT_ENGAGEMENT * eng_score
        )

        # HN data is always from API, so always verified
        if item.engagement_verified:
            overall += VERIFIED_ENGAGEMENT_BONUS
        elif eng_raw[i] is None:
            overall -= UNKNOWN_ENGAGEMENT_PENALTY

        # Apply penalty for low date confidence (rare for HN)
        if item.date_confidence == "low":
            overall -= 10
        elif item.date_confidence == "med":
            overall -= 5

        item.score = max(0, min(100, int(overall)))

    return items


def score_websearch_items(items: List[schema.WebSearchItem]) -> List[schema.WebSearchItem]:
    """Compute scores for WebSearch items WITHOUT engagement metrics.

    Uses reweighted formula: 55% relevance + 45% recency - 15pt source penalty.
    This ensures WebSearch items rank below comparable Reddit/X items.

    Date confidence adjustments:
    - High confidence (URL-verified date): +10 bonus
    - Med confidence (snippet-extracted date): no change
    - Low confidence (no date signals): -20 penalty

    Args:
        items: List of WebSearch items

    Returns:
        Items with updated scores
    """
    if not items:
        return items

    for item in items:
        # Relevance subscore (model-provided, convert to 0-100)
        rel_score = int(item.relevance * 100)

        # Recency subscore
        rec_score = dates.recency_score(item.date)

        # Store subscores (engagement is 0 for WebSearch - no data)
        item.subs = schema.SubScores(
            relevance=rel_score,
            recency=rec_score,
            engagement=0,  # Explicitly zero - no engagement data available
        )

        # Compute overall score using WebSearch weights
        overall = (
            WEBSEARCH_WEIGHT_RELEVANCE * rel_score +
            WEBSEARCH_WEIGHT_RECENCY * rec_score
        )

        # Apply source penalty (WebSearch < Reddit/X for same relevance/recency)
        overall -= WEBSEARCH_SOURCE_PENALTY

        # Apply date confidence adjustments
        # High confidence (URL-verified): reward with bonus
        # Med confidence (snippet-extracted): neutral
        # Low confidence (no date signals): heavy penalty
        if item.date_confidence == "high":
            overall += WEBSEARCH_VERIFIED_BONUS  # Reward verified recent dates
        elif item.date_confidence == "low":
            overall -= WEBSEARCH_NO_DATE_PENALTY  # Heavy penalty for unknown

        item.score = max(0, min(100, int(overall)))

    return items


def sort_items(items: List[Union[schema.RedditItem, schema.XItem, schema.HNItem, schema.WebSearchItem]]) -> List:
    """Sort items by score (descending), then date, then source priority.

    Args:
        items: List of items to sort

    Returns:
        Sorted items
    """
    def sort_key(item):
        # Primary: score descending (negate for descending)
        score = -item.score

        # Secondary: date descending (recent first)
        date = item.date or "0000-00-00"
        date_key = -int(date.replace("-", ""))

        # Tertiary: source priority (Reddit > X > HN > WebSearch)
        if isinstance(item, schema.RedditItem):
            source_priority = 0
        elif isinstance(item, schema.XItem):
            source_priority = 1
        elif isinstance(item, schema.HNItem):
            source_priority = 2
        else:  # WebSearchItem
            source_priority = 3

        # Quaternary: title/text for stability
        text = getattr(item, "title", "") or getattr(item, "text", "")

        return (score, date_key, source_priority, text)

    return sorted(items, key=sort_key)
