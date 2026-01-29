"""Data schemas for last30days skill."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class Engagement:
    """Engagement metrics."""
    # Reddit fields
    score: Optional[int] = None
    num_comments: Optional[int] = None
    upvote_ratio: Optional[float] = None

    # X fields
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None

    # HackerNews fields
    points: Optional[int] = None  # HN upvotes

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.score is not None:
            d['score'] = self.score
        if self.num_comments is not None:
            d['num_comments'] = self.num_comments
        if self.upvote_ratio is not None:
            d['upvote_ratio'] = self.upvote_ratio
        if self.likes is not None:
            d['likes'] = self.likes
        if self.reposts is not None:
            d['reposts'] = self.reposts
        if self.replies is not None:
            d['replies'] = self.replies
        if self.quotes is not None:
            d['quotes'] = self.quotes
        if self.points is not None:
            d['points'] = self.points
        return d if d else None


@dataclass
class Comment:
    """Reddit comment."""
    score: int
    date: Optional[str]
    author: str
    excerpt: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'date': self.date,
            'author': self.author,
            'excerpt': self.excerpt,
            'url': self.url,
        }


@dataclass
class SubScores:
    """Component scores."""
    relevance: int = 0
    recency: int = 0
    engagement: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            'relevance': self.relevance,
            'recency': self.recency,
            'engagement': self.engagement,
        }


@dataclass
class RedditItem:
    """Normalized Reddit item."""
    id: str
    title: str
    url: str
    subreddit: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    engagement_verified: bool = False  # True if engagement from Reddit JSON, not estimated
    top_comments: List[Comment] = field(default_factory=list)
    comment_insights: List[str] = field(default_factory=list)
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'subreddit': self.subreddit,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'engagement_verified': self.engagement_verified,
            'top_comments': [c.to_dict() for c in self.top_comments],
            'comment_insights': self.comment_insights,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class XItem:
    """Normalized X item."""
    id: str
    text: str
    url: str
    author_handle: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    engagement_verified: bool = False  # True if engagement from X API directly
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text,
            'url': self.url,
            'author_handle': self.author_handle,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'engagement_verified': self.engagement_verified,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class HNItem:
    """Normalized HackerNews item."""
    id: str
    title: str
    url: str
    hn_url: str  # HackerNews discussion link
    author: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    engagement_verified: bool = True  # HN data is always from API
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'hn_url': self.hn_url,
            'author': self.author,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'engagement_verified': self.engagement_verified,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class WebSearchItem:
    """Normalized web search item (no engagement metrics)."""
    id: str
    title: str
    url: str
    source_domain: str  # e.g., "medium.com", "github.com"
    snippet: str
    date: Optional[str] = None
    date_confidence: str = "low"
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'source_domain': self.source_domain,
            'snippet': self.snippet,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class DataQuality:
    """Data quality metrics for transparency."""
    total_items: int = 0
    verified_dates_count: int = 0
    verified_engagement_count: int = 0
    avg_recency_days: float = 0.0
    sources_available: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    fallback_models_used: List[str] = field(default_factory=list)

    @property
    def verified_dates_percent(self) -> float:
        return (self.verified_dates_count / self.total_items * 100) if self.total_items > 0 else 0

    @property
    def verified_engagement_percent(self) -> float:
        return (self.verified_engagement_count / self.total_items * 100) if self.total_items > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_items': self.total_items,
            'verified_dates_count': self.verified_dates_count,
            'verified_dates_percent': round(self.verified_dates_percent, 1),
            'verified_engagement_count': self.verified_engagement_count,
            'verified_engagement_percent': round(self.verified_engagement_percent, 1),
            'avg_recency_days': round(self.avg_recency_days, 1),
            'sources_available': self.sources_available,
            'sources_failed': self.sources_failed,
            'fallback_models_used': self.fallback_models_used,
        }


@dataclass
class Report:
    """Full research report."""
    topic: str
    range_from: str
    range_to: str
    generated_at: str
    mode: str  # 'reddit-only', 'x-only', 'both', 'web-only', 'all', etc.
    openai_model_used: Optional[str] = None
    xai_model_used: Optional[str] = None
    reddit: List[RedditItem] = field(default_factory=list)
    x: List[XItem] = field(default_factory=list)
    hn: List[HNItem] = field(default_factory=list)  # HackerNews items
    web: List[WebSearchItem] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    prompt_pack: List[str] = field(default_factory=list)
    context_snippet_md: str = ""
    # Status tracking
    reddit_error: Optional[str] = None
    x_error: Optional[str] = None
    hn_error: Optional[str] = None  # HackerNews error
    web_error: Optional[str] = None
    # Cache info
    from_cache: bool = False
    cache_age_hours: Optional[float] = None
    # Data quality metrics
    data_quality: Optional[DataQuality] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'topic': self.topic,
            'range': {
                'from': self.range_from,
                'to': self.range_to,
            },
            'generated_at': self.generated_at,
            'mode': self.mode,
            'openai_model_used': self.openai_model_used,
            'xai_model_used': self.xai_model_used,
            'reddit': [r.to_dict() for r in self.reddit],
            'x': [x.to_dict() for x in self.x],
            'hn': [h.to_dict() for h in self.hn],
            'web': [w.to_dict() for w in self.web],
            'best_practices': self.best_practices,
            'prompt_pack': self.prompt_pack,
            'context_snippet_md': self.context_snippet_md,
        }
        if self.reddit_error:
            d['reddit_error'] = self.reddit_error
        if self.x_error:
            d['x_error'] = self.x_error
        if self.hn_error:
            d['hn_error'] = self.hn_error
        if self.web_error:
            d['web_error'] = self.web_error
        if self.from_cache:
            d['from_cache'] = self.from_cache
        if self.cache_age_hours is not None:
            d['cache_age_hours'] = self.cache_age_hours
        if self.data_quality:
            d['data_quality'] = self.data_quality.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """Create Report from serialized dict (handles cache format)."""
        # Handle range field conversion
        range_data = data.get('range', {})
        range_from = range_data.get('from', data.get('range_from', ''))
        range_to = range_data.get('to', data.get('range_to', ''))

        # Reconstruct Reddit items
        reddit_items = []
        for r in data.get('reddit', []):
            eng = None
            if r.get('engagement'):
                eng = Engagement(**r['engagement'])
            comments = [Comment(**c) for c in r.get('top_comments', [])]
            subs = SubScores(**r.get('subs', {})) if r.get('subs') else SubScores()
            reddit_items.append(RedditItem(
                id=r['id'],
                title=r['title'],
                url=r['url'],
                subreddit=r['subreddit'],
                date=r.get('date'),
                date_confidence=r.get('date_confidence', 'low'),
                engagement=eng,
                engagement_verified=r.get('engagement_verified', False),
                top_comments=comments,
                comment_insights=r.get('comment_insights', []),
                relevance=r.get('relevance', 0.5),
                why_relevant=r.get('why_relevant', ''),
                subs=subs,
                score=r.get('score', 0),
            ))

        # Reconstruct X items
        x_items = []
        for x in data.get('x', []):
            eng = None
            if x.get('engagement'):
                eng = Engagement(**x['engagement'])
            subs = SubScores(**x.get('subs', {})) if x.get('subs') else SubScores()
            x_items.append(XItem(
                id=x['id'],
                text=x['text'],
                url=x['url'],
                author_handle=x['author_handle'],
                date=x.get('date'),
                date_confidence=x.get('date_confidence', 'low'),
                engagement=eng,
                engagement_verified=x.get('engagement_verified', False),
                relevance=x.get('relevance', 0.5),
                why_relevant=x.get('why_relevant', ''),
                subs=subs,
                score=x.get('score', 0),
            ))

        # Reconstruct Web items
        web_items = []
        for w in data.get('web', []):
            subs = SubScores(**w.get('subs', {})) if w.get('subs') else SubScores()
            web_items.append(WebSearchItem(
                id=w['id'],
                title=w['title'],
                url=w['url'],
                source_domain=w.get('source_domain', ''),
                snippet=w.get('snippet', ''),
                date=w.get('date'),
                date_confidence=w.get('date_confidence', 'low'),
                relevance=w.get('relevance', 0.5),
                why_relevant=w.get('why_relevant', ''),
                subs=subs,
                score=w.get('score', 0),
            ))

        # Reconstruct HN items
        hn_items = []
        for h in data.get('hn', []):
            eng = None
            if h.get('engagement'):
                eng = Engagement(**h['engagement'])
            subs = SubScores(**h.get('subs', {})) if h.get('subs') else SubScores()
            hn_items.append(HNItem(
                id=h['id'],
                title=h['title'],
                url=h['url'],
                hn_url=h.get('hn_url', ''),
                author=h.get('author', ''),
                date=h.get('date'),
                date_confidence=h.get('date_confidence', 'low'),
                engagement=eng,
                engagement_verified=h.get('engagement_verified', True),
                relevance=h.get('relevance', 0.5),
                why_relevant=h.get('why_relevant', ''),
                subs=subs,
                score=h.get('score', 0),
            ))

        return cls(
            topic=data['topic'],
            range_from=range_from,
            range_to=range_to,
            generated_at=data['generated_at'],
            mode=data['mode'],
            openai_model_used=data.get('openai_model_used'),
            xai_model_used=data.get('xai_model_used'),
            reddit=reddit_items,
            x=x_items,
            hn=hn_items,
            web=web_items,
            best_practices=data.get('best_practices', []),
            prompt_pack=data.get('prompt_pack', []),
            context_snippet_md=data.get('context_snippet_md', ''),
            reddit_error=data.get('reddit_error'),
            x_error=data.get('x_error'),
            hn_error=data.get('hn_error'),
            web_error=data.get('web_error'),
            from_cache=data.get('from_cache', False),
            cache_age_hours=data.get('cache_age_hours'),
        )


def create_report(
    topic: str,
    from_date: str,
    to_date: str,
    mode: str,
    openai_model: Optional[str] = None,
    xai_model: Optional[str] = None,
) -> Report:
    """Create a new report with metadata."""
    return Report(
        topic=topic,
        range_from=from_date,
        range_to=to_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        openai_model_used=openai_model,
        xai_model_used=xai_model,
    )


def compute_data_quality(report: Report) -> DataQuality:
    """Compute data quality metrics for a report.

    Args:
        report: The report to analyze

    Returns:
        DataQuality metrics object
    """
    all_items = list(report.reddit) + list(report.x) + list(report.hn) + list(report.web)
    total = len(all_items)

    if total == 0:
        return DataQuality(total_items=0)

    # Count verified dates (high confidence)
    verified_dates = sum(1 for item in all_items if item.date_confidence == "high")

    # Count verified engagement
    verified_engagement = 0
    for item in report.reddit:
        if item.engagement_verified:
            verified_engagement += 1
    for item in report.x:
        if item.engagement_verified:
            verified_engagement += 1
    for item in report.hn:
        if item.engagement_verified:
            verified_engagement += 1
    # WebSearch items don't have engagement

    # Calculate average recency
    from . import dates as dates_module
    recency_days = []
    for item in all_items:
        if item.date:
            age = dates_module.days_ago(item.date)
            if age is not None:
                recency_days.append(age)
    avg_recency = sum(recency_days) / len(recency_days) if recency_days else 30.0

    # Determine sources used
    sources_available = []
    sources_failed = []
    if report.reddit:
        sources_available.append("reddit")
    elif report.reddit_error:
        sources_failed.append("reddit")
    if report.x:
        sources_available.append("x")
    elif report.x_error:
        sources_failed.append("x")
    if report.hn:
        sources_available.append("hn")
    elif report.hn_error:
        sources_failed.append("hn")
    if report.web:
        sources_available.append("web")
    elif report.web_error:
        sources_failed.append("web")

    return DataQuality(
        total_items=total,
        verified_dates_count=verified_dates,
        verified_engagement_count=verified_engagement,
        avg_recency_days=avg_recency,
        sources_available=sources_available,
        sources_failed=sources_failed,
    )
