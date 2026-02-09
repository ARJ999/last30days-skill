"""Near-duplicate detection and cross-source URL deduplication for last30days skill."""

import re
from typing import Dict, List, Set, Tuple, Union
from urllib.parse import urlparse

from . import schema

# Type alias for all item types
AnyItem = Union[
    schema.RedditItem, schema.XItem, schema.HNItem,
    schema.NewsItem, schema.WebItem, schema.VideoItem, schema.DiscussionItem,
]


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_ngrams(text: str, n: int = 3) -> Set[str]:
    """Get character n-grams from text."""
    text = normalize_text(text)
    if len(text) < n:
        return {text}
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def get_item_text(item: AnyItem) -> str:
    """Get comparable text from an item."""
    if isinstance(item, schema.XItem):
        return item.text
    return getattr(item, "title", "") or ""


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (strip scheme, www, trailing slash, query params)."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").removeprefix("www.")
        path = parsed.path.rstrip("/")
        return f"{hostname}{path}".lower()
    except Exception:
        return url.lower()


def find_duplicates(
    items: List[AnyItem],
    threshold: float = 0.7,
) -> List[Tuple[int, int]]:
    """Find near-duplicate pairs in items based on text similarity."""
    duplicates = []
    ngrams = [get_ngrams(get_item_text(item)) for item in items]

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            similarity = jaccard_similarity(ngrams[i], ngrams[j])
            if similarity >= threshold:
                duplicates.append((i, j))

    return duplicates


def dedupe_items(
    items: List[AnyItem],
    threshold: float = 0.7,
) -> List[AnyItem]:
    """Remove near-duplicates within a single source, keeping highest-scored item."""
    if len(items) <= 1:
        return items

    dup_pairs = find_duplicates(items, threshold)

    to_remove = set()
    for i, j in dup_pairs:
        if items[i].score >= items[j].score:
            to_remove.add(j)
        else:
            to_remove.add(i)

    return [item for idx, item in enumerate(items) if idx not in to_remove]


def dedupe_reddit(items: List[schema.RedditItem], threshold: float = 0.7) -> List[schema.RedditItem]:
    """Dedupe Reddit items."""
    return dedupe_items(items, threshold)


def dedupe_x(items: List[schema.XItem], threshold: float = 0.7) -> List[schema.XItem]:
    """Dedupe X items."""
    return dedupe_items(items, threshold)


def dedupe_hn(items: List[schema.HNItem], threshold: float = 0.7) -> List[schema.HNItem]:
    """Dedupe HackerNews items."""
    return dedupe_items(items, threshold)


def dedupe_news(items: List[schema.NewsItem], threshold: float = 0.7) -> List[schema.NewsItem]:
    """Dedupe News items."""
    return dedupe_items(items, threshold)


def dedupe_web(items: List[schema.WebItem], threshold: float = 0.7) -> List[schema.WebItem]:
    """Dedupe Web items."""
    return dedupe_items(items, threshold)


def dedupe_videos(items: List[schema.VideoItem], threshold: float = 0.7) -> List[schema.VideoItem]:
    """Dedupe Video items."""
    return dedupe_items(items, threshold)


def dedupe_discussions(items: List[schema.DiscussionItem], threshold: float = 0.7) -> List[schema.DiscussionItem]:
    """Dedupe Discussion items."""
    return dedupe_items(items, threshold)


def cross_source_url_dedupe(
    reddit: List[schema.RedditItem],
    x: List[schema.XItem],
    hn: List[schema.HNItem],
    news: List[schema.NewsItem],
    web: List[schema.WebItem],
    videos: List[schema.VideoItem],
    discussions: List[schema.DiscussionItem],
) -> Tuple[
    List[schema.RedditItem],
    List[schema.XItem],
    List[schema.HNItem],
    List[schema.NewsItem],
    List[schema.WebItem],
    List[schema.VideoItem],
    List[schema.DiscussionItem],
]:
    """Remove URLs that appear in multiple sources, keeping highest-priority source.

    Priority order: Reddit > X > HN > News > Discussions > Web > Videos
    This ensures that a URL appearing in both Reddit (with engagement data) and
    Web (without) keeps only the richer Reddit version.

    Returns:
        Tuple of all 7 deduped lists in the same order as input.
    """
    seen_urls: Dict[str, str] = {}  # normalized_url -> source_name

    # Process in priority order (highest priority first claims the URL)
    source_lists = [
        ("reddit", reddit),
        ("x", x),
        ("hn", hn),
        ("news", news),
        ("discussions", discussions),
        ("web", web),
        ("videos", videos),
    ]

    # First pass: collect all URLs from higher-priority sources
    for source_name, items in source_lists:
        for item in items:
            url_key = normalize_url(item.url)
            if url_key not in seen_urls:
                seen_urls[url_key] = source_name

                # For HN items, also claim the linked URL
                if isinstance(item, schema.HNItem) and item.hn_url:
                    hn_key = normalize_url(item.hn_url)
                    if hn_key not in seen_urls:
                        seen_urls[hn_key] = source_name

    # Second pass: filter out items whose URL was claimed by a higher-priority source
    def _filter(items: list, source_name: str) -> list:
        result = []
        for item in items:
            url_key = normalize_url(item.url)
            owner = seen_urls.get(url_key, source_name)
            if owner == source_name:
                result.append(item)
        return result

    return (
        _filter(reddit, "reddit"),
        _filter(x, "x"),
        _filter(hn, "hn"),
        _filter(news, "news"),
        _filter(web, "web"),
        _filter(videos, "videos"),
        _filter(discussions, "discussions"),
    )
