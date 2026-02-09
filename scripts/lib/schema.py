"""Data schemas for last30days skill."""

from dataclasses import dataclass, field
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
    points: Optional[int] = None

    def to_dict(self) -> Optional[Dict[str, Any]]:
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
    engagement_verified: bool = False
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
    engagement_verified: bool = False
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
    hn_url: str
    author: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    engagement_verified: bool = True
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
class NewsItem:
    """Normalized news article from Brave News Search."""
    id: str
    title: str
    url: str
    source_name: str
    source_domain: str
    date: Optional[str] = None
    date_confidence: str = "high"
    snippet: str = ""
    extra_snippets: List[str] = field(default_factory=list)
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'source_name': self.source_name,
            'source_domain': self.source_domain,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'snippet': self.snippet,
            'extra_snippets': self.extra_snippets,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class WebItem:
    """Normalized web result from Brave Web Search."""
    id: str
    title: str
    url: str
    source_domain: str
    snippet: str = ""
    extra_snippets: List[str] = field(default_factory=list)
    date: Optional[str] = None
    date_confidence: str = "high"
    has_schema_data: bool = False
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
            'extra_snippets': self.extra_snippets,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'has_schema_data': self.has_schema_data,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class VideoItem:
    """Normalized video result from Brave Video Search."""
    id: str
    title: str
    url: str
    source_domain: str
    creator: Optional[str] = None
    date: Optional[str] = None
    date_confidence: str = "high"
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    snippet: str = ""
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
            'creator': self.creator,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'thumbnail_url': self.thumbnail_url,
            'duration': self.duration,
            'snippet': self.snippet,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class DiscussionItem:
    """Normalized discussion/forum result from Brave Discussions."""
    id: str
    title: str
    url: str
    forum_name: str
    date: Optional[str] = None
    date_confidence: str = "high"
    snippet: str = ""
    extra_snippets: List[str] = field(default_factory=list)
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'forum_name': self.forum_name,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'snippet': self.snippet,
            'extra_snippets': self.extra_snippets,
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
    has_summary: bool = False
    has_infobox: bool = False
    faq_count: int = 0

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
            'has_summary': self.has_summary,
            'has_infobox': self.has_infobox,
            'faq_count': self.faq_count,
        }


@dataclass
class Report:
    """Full research report."""
    topic: str
    range_from: str
    range_to: str
    generated_at: str
    mode: str

    # Model used (xAI only now)
    xai_model_used: Optional[str] = None

    # Primary social sources (engagement-verified)
    reddit: List[RedditItem] = field(default_factory=list)
    x: List[XItem] = field(default_factory=list)
    hn: List[HNItem] = field(default_factory=list)

    # Brave-powered sources
    news: List[NewsItem] = field(default_factory=list)
    web: List[WebItem] = field(default_factory=list)
    videos: List[VideoItem] = field(default_factory=list)
    discussions: List[DiscussionItem] = field(default_factory=list)

    # Brave enrichment data
    summary: Optional[str] = None
    summary_citations: List[Dict] = field(default_factory=list)
    summary_followups: List[str] = field(default_factory=list)
    infobox: Optional[Dict] = None
    faqs: List[Dict] = field(default_factory=list)

    # Errors per source
    reddit_error: Optional[str] = None
    x_error: Optional[str] = None
    hn_error: Optional[str] = None
    news_error: Optional[str] = None
    web_error: Optional[str] = None
    video_error: Optional[str] = None

    # Cache info
    from_cache: bool = False
    cache_age_hours: Optional[float] = None

    # Context snippet
    context_snippet_md: str = ""

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
            'xai_model_used': self.xai_model_used,
            'reddit': [r.to_dict() for r in self.reddit],
            'x': [x.to_dict() for x in self.x],
            'hn': [h.to_dict() for h in self.hn],
            'news': [n.to_dict() for n in self.news],
            'web': [w.to_dict() for w in self.web],
            'videos': [v.to_dict() for v in self.videos],
            'discussions': [d_.to_dict() for d_ in self.discussions],
        }

        # Brave enrichment
        if self.summary:
            d['summary'] = self.summary
        if self.summary_citations:
            d['summary_citations'] = self.summary_citations
        if self.summary_followups:
            d['summary_followups'] = self.summary_followups
        if self.infobox:
            d['infobox'] = self.infobox
        if self.faqs:
            d['faqs'] = self.faqs

        # Errors
        if self.reddit_error:
            d['reddit_error'] = self.reddit_error
        if self.x_error:
            d['x_error'] = self.x_error
        if self.hn_error:
            d['hn_error'] = self.hn_error
        if self.news_error:
            d['news_error'] = self.news_error
        if self.web_error:
            d['web_error'] = self.web_error
        if self.video_error:
            d['video_error'] = self.video_error

        # Cache
        if self.from_cache:
            d['from_cache'] = self.from_cache
        if self.cache_age_hours is not None:
            d['cache_age_hours'] = self.cache_age_hours

        if self.context_snippet_md:
            d['context_snippet_md'] = self.context_snippet_md

        if self.data_quality:
            d['data_quality'] = self.data_quality.to_dict()

        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """Create Report from serialized dict (handles cache format)."""
        range_data = data.get('range', {})
        range_from = range_data.get('from', data.get('range_from', ''))
        range_to = range_data.get('to', data.get('range_to', ''))

        def _build_engagement(raw: Optional[Dict]) -> Optional[Engagement]:
            if not raw:
                return None
            return Engagement(**raw)

        def _build_subs(raw: Optional[Dict]) -> SubScores:
            if not raw:
                return SubScores()
            return SubScores(**raw)

        # Reconstruct Reddit items
        reddit_items = []
        for r in data.get('reddit', []):
            comments = [Comment(**c) for c in r.get('top_comments', [])]
            reddit_items.append(RedditItem(
                id=r['id'], title=r['title'], url=r['url'],
                subreddit=r['subreddit'],
                date=r.get('date'), date_confidence=r.get('date_confidence', 'low'),
                engagement=_build_engagement(r.get('engagement')),
                engagement_verified=r.get('engagement_verified', False),
                top_comments=comments,
                comment_insights=r.get('comment_insights', []),
                relevance=r.get('relevance', 0.5),
                why_relevant=r.get('why_relevant', ''),
                subs=_build_subs(r.get('subs')),
                score=r.get('score', 0),
            ))

        # Reconstruct X items
        x_items = []
        for x in data.get('x', []):
            x_items.append(XItem(
                id=x['id'], text=x['text'], url=x['url'],
                author_handle=x['author_handle'],
                date=x.get('date'), date_confidence=x.get('date_confidence', 'low'),
                engagement=_build_engagement(x.get('engagement')),
                engagement_verified=x.get('engagement_verified', False),
                relevance=x.get('relevance', 0.5),
                why_relevant=x.get('why_relevant', ''),
                subs=_build_subs(x.get('subs')),
                score=x.get('score', 0),
            ))

        # Reconstruct HN items
        hn_items = []
        for h in data.get('hn', []):
            hn_items.append(HNItem(
                id=h['id'], title=h['title'], url=h['url'],
                hn_url=h.get('hn_url', ''), author=h.get('author', ''),
                date=h.get('date'), date_confidence=h.get('date_confidence', 'low'),
                engagement=_build_engagement(h.get('engagement')),
                engagement_verified=h.get('engagement_verified', True),
                relevance=h.get('relevance', 0.5),
                why_relevant=h.get('why_relevant', ''),
                subs=_build_subs(h.get('subs')),
                score=h.get('score', 0),
            ))

        # Reconstruct News items
        news_items = []
        for n in data.get('news', []):
            news_items.append(NewsItem(
                id=n['id'], title=n['title'], url=n['url'],
                source_name=n.get('source_name', ''),
                source_domain=n.get('source_domain', ''),
                date=n.get('date'), date_confidence=n.get('date_confidence', 'high'),
                snippet=n.get('snippet', ''),
                extra_snippets=n.get('extra_snippets', []),
                relevance=n.get('relevance', 0.5),
                why_relevant=n.get('why_relevant', ''),
                subs=_build_subs(n.get('subs')),
                score=n.get('score', 0),
            ))

        # Reconstruct Web items
        web_items = []
        for w in data.get('web', []):
            web_items.append(WebItem(
                id=w['id'], title=w['title'], url=w['url'],
                source_domain=w.get('source_domain', ''),
                snippet=w.get('snippet', ''),
                extra_snippets=w.get('extra_snippets', []),
                date=w.get('date'), date_confidence=w.get('date_confidence', 'high'),
                has_schema_data=w.get('has_schema_data', False),
                relevance=w.get('relevance', 0.5),
                why_relevant=w.get('why_relevant', ''),
                subs=_build_subs(w.get('subs')),
                score=w.get('score', 0),
            ))

        # Reconstruct Video items
        video_items = []
        for v in data.get('videos', []):
            video_items.append(VideoItem(
                id=v['id'], title=v['title'], url=v['url'],
                source_domain=v.get('source_domain', ''),
                creator=v.get('creator'),
                date=v.get('date'), date_confidence=v.get('date_confidence', 'high'),
                thumbnail_url=v.get('thumbnail_url'),
                duration=v.get('duration'),
                snippet=v.get('snippet', ''),
                relevance=v.get('relevance', 0.5),
                why_relevant=v.get('why_relevant', ''),
                subs=_build_subs(v.get('subs')),
                score=v.get('score', 0),
            ))

        # Reconstruct Discussion items
        discussion_items = []
        for d_ in data.get('discussions', []):
            discussion_items.append(DiscussionItem(
                id=d_['id'], title=d_['title'], url=d_['url'],
                forum_name=d_.get('forum_name', ''),
                date=d_.get('date'), date_confidence=d_.get('date_confidence', 'high'),
                snippet=d_.get('snippet', ''),
                extra_snippets=d_.get('extra_snippets', []),
                relevance=d_.get('relevance', 0.5),
                why_relevant=d_.get('why_relevant', ''),
                subs=_build_subs(d_.get('subs')),
                score=d_.get('score', 0),
            ))

        return cls(
            topic=data['topic'],
            range_from=range_from,
            range_to=range_to,
            generated_at=data['generated_at'],
            mode=data['mode'],
            xai_model_used=data.get('xai_model_used'),
            reddit=reddit_items,
            x=x_items,
            hn=hn_items,
            news=news_items,
            web=web_items,
            videos=video_items,
            discussions=discussion_items,
            summary=data.get('summary'),
            summary_citations=data.get('summary_citations', []),
            summary_followups=data.get('summary_followups', []),
            infobox=data.get('infobox'),
            faqs=data.get('faqs', []),
            reddit_error=data.get('reddit_error'),
            x_error=data.get('x_error'),
            hn_error=data.get('hn_error'),
            news_error=data.get('news_error'),
            web_error=data.get('web_error'),
            video_error=data.get('video_error'),
            from_cache=data.get('from_cache', False),
            cache_age_hours=data.get('cache_age_hours'),
            context_snippet_md=data.get('context_snippet_md', ''),
        )


def create_report(
    topic: str,
    from_date: str,
    to_date: str,
    mode: str,
    xai_model: Optional[str] = None,
) -> Report:
    """Create a new report with metadata."""
    return Report(
        topic=topic,
        range_from=from_date,
        range_to=to_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        xai_model_used=xai_model,
    )


def compute_data_quality(report: Report) -> DataQuality:
    """Compute data quality metrics for a report."""
    all_items = (
        list(report.reddit) + list(report.x) + list(report.hn) +
        list(report.news) + list(report.web) + list(report.videos) +
        list(report.discussions)
    )
    total = len(all_items)

    if total == 0:
        return DataQuality(total_items=0)

    # Count verified dates (high confidence)
    verified_dates = sum(1 for item in all_items if item.date_confidence == "high")

    # Count verified engagement (Reddit enriched + X + HN)
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

    # Calculate average recency
    from . import dates as dates_module
    recency_days = []
    for item in all_items:
        if item.date:
            age = dates_module.days_ago(item.date)
            if age is not None:
                recency_days.append(age)
    avg_recency = sum(recency_days) / len(recency_days) if recency_days else 30.0

    # Determine sources used/failed
    source_map = [
        ("reddit", report.reddit, report.reddit_error),
        ("x", report.x, report.x_error),
        ("hn", report.hn, report.hn_error),
        ("news", report.news, report.news_error),
        ("web", report.web, report.web_error),
        ("videos", report.videos, report.video_error),
        ("discussions", report.discussions, None),
    ]

    sources_available = []
    sources_failed = []
    for name, items, error in source_map:
        if items:
            sources_available.append(name)
        elif error:
            sources_failed.append(name)

    return DataQuality(
        total_items=total,
        verified_dates_count=verified_dates,
        verified_engagement_count=verified_engagement,
        avg_recency_days=avg_recency,
        sources_available=sources_available,
        sources_failed=sources_failed,
        has_summary=report.summary is not None,
        has_infobox=report.infobox is not None,
        faq_count=len(report.faqs),
    )
