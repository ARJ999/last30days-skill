"""Output rendering for last30days skill."""

import json
from pathlib import Path
from typing import List, Optional

from . import schema

OUTPUT_DIR = Path.home() / ".local" / "share" / "last30days" / "out"


def _format_count(n: int) -> str:
    """Format large numbers for compact display (e.g. 10500 -> '10.5K')."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def ensure_output_dir():
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _assess_data_freshness(report: schema.Report) -> dict:
    """Assess how much data is actually from the last 30 days."""
    all_source_lists = [
        report.reddit, report.x, report.hn,
        report.news, report.web, report.videos, report.discussions,
    ]

    total_recent = 0
    total_items = 0
    for items in all_source_lists:
        for item in items:
            total_items += 1
            if item.date and item.date >= report.range_from:
                total_recent += 1

    return {
        "total_recent": total_recent,
        "total_items": total_items,
        "is_sparse": total_recent < 5,
        "mostly_evergreen": total_items > 0 and total_recent < total_items * 0.3,
    }


def render_compact(report: schema.Report, limit: int = 15, missing_keys: str = "none") -> str:
    """Render compact output for Claude to synthesize."""
    lines = []

    # Header
    lines.append(f"## Research Results: {report.topic}")
    lines.append("")

    # Assess data freshness
    freshness = _assess_data_freshness(report)
    if freshness["is_sparse"]:
        lines.append("**LIMITED RECENT DATA** - Few discussions from the last 30 days.")
        lines.append(f"Only {freshness['total_recent']} item(s) confirmed from {report.range_from} to {report.range_to}.")
        lines.append("Results below may include older/evergreen content. Be transparent with the user about this.")
        lines.append("")

    # HN-only mode banner
    if report.mode == "hn-only":
        lines.append("**HN ONLY MODE** - Only HackerNews available (no API keys configured)")
        lines.append("")
        lines.append("---")
        lines.append("**Want better results?** Add API keys to unlock more sources:")
        lines.append("- `BRAVE_API_KEY` -> Reddit, News, Web, Videos, Discussions")
        lines.append("- `XAI_API_KEY` -> X/Twitter posts with real engagement")
        lines.append("- Edit `~/.config/last30days/.env` to add keys")
        lines.append("---")
        lines.append("")

    # Cache indicator
    if report.from_cache:
        age_str = f"{report.cache_age_hours:.1f}h old" if report.cache_age_hours else "cached"
        lines.append(f"**CACHED RESULTS** ({age_str}) - use `--refresh` for fresh data")
        lines.append("")

    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")
    lines.append(f"**Mode:** {report.mode}")
    if report.xai_model_used:
        lines.append(f"**xAI Model:** {report.xai_model_used}")
    lines.append("")

    # Coverage tip for partial coverage
    if missing_keys == "brave":
        lines.append("*Tip: Add BRAVE_API_KEY for Reddit, News, Web, Videos, and Discussions data.*")
        lines.append("")
    elif missing_keys == "x":
        lines.append("*Tip: Add XAI_API_KEY for X/Twitter data with real likes & reposts.*")
        lines.append("")
    elif missing_keys == "both":
        lines.append("*Tip: Add BRAVE_API_KEY and XAI_API_KEY for full source coverage.*")
        lines.append("")

    # Data quality metrics
    if report.data_quality:
        dq = report.data_quality
        lines.append("### Data Quality")
        lines.append(f"- **Total Items:** {dq.total_items}")
        lines.append(f"- **Verified Dates:** {dq.verified_dates_count} ({dq.verified_dates_percent:.0f}%)")
        lines.append(f"- **Verified Engagement:** {dq.verified_engagement_count} ({dq.verified_engagement_percent:.0f}%)")
        lines.append(f"- **Avg Recency:** {dq.avg_recency_days:.1f} days")
        if dq.sources_available:
            lines.append(f"- **Sources Used:** {', '.join(dq.sources_available)}")
        if dq.sources_failed:
            lines.append(f"- **Sources Failed:** {', '.join(dq.sources_failed)}")
        if dq.has_summary:
            lines.append("- **AI Summary:** Available")
        if dq.has_infobox:
            lines.append("- **Knowledge Panel:** Available")
        if dq.faq_count > 0:
            lines.append(f"- **FAQ Entries:** {dq.faq_count}")
        lines.append("")

    # AI Summary (from Brave Summarizer)
    if report.summary:
        lines.append("### AI Summary")
        lines.append("")
        lines.append(report.summary)
        if report.summary_citations:
            lines.append("")
            lines.append("**Citations:**")
            for cite in report.summary_citations[:10]:
                num = cite.get("number", "")
                title = cite.get("title", "")
                url = cite.get("url", "")
                if url:
                    lines.append(f"  [{num}] {title} - {url}")
        if report.summary_followups:
            lines.append("")
            lines.append("**Related questions:**")
            for q in report.summary_followups[:5]:
                lines.append(f"  - {q}")
        lines.append("")

    # Infobox (Knowledge Panel)
    if report.infobox:
        ib = report.infobox
        lines.append("### Knowledge Panel")
        lines.append("")
        if ib.get("title"):
            lines.append(f"**{ib['title']}**")
        if ib.get("description"):
            lines.append(ib["description"])
        if ib.get("long_description"):
            lines.append(ib["long_description"][:300])
        if ib.get("url"):
            lines.append(f"Source: {ib['url']}")
        lines.append("")

    # FAQ
    if report.faqs:
        lines.append("### Frequently Asked Questions")
        lines.append("")
        for faq in report.faqs[:5]:
            lines.append(f"**Q: {faq.get('question', '')}**")
            lines.append(f"A: {faq.get('answer', '')}")
            if faq.get("url"):
                lines.append(f"Source: {faq['url']}")
            lines.append("")

    # Reddit items
    _render_reddit_section(lines, report, limit)

    # X items
    _render_x_section(lines, report, limit)

    # HackerNews items
    _render_hn_section(lines, report, limit)

    # News items
    _render_news_section(lines, report, limit)

    # Web items
    _render_web_section(lines, report, limit)

    # Video items
    _render_video_section(lines, report, limit)

    # Discussion items
    _render_discussion_section(lines, report, limit)

    return "\n".join(lines)


def _render_reddit_section(lines: list, report: schema.Report, limit: int):
    """Render Reddit section."""
    if report.reddit_error:
        lines.append("### Reddit Threads")
        lines.append("")
        lines.append(f"**ERROR:** {report.reddit_error}")
        lines.append("")
    elif report.reddit:
        lines.append("### Reddit Threads")
        lines.append("")
        for item in report.reddit[:limit]:
            eng_str = ""
            if item.engagement:
                eng = item.engagement
                parts = []
                if eng.score is not None:
                    parts.append(f"{eng.score}pts")
                if eng.num_comments is not None:
                    parts.append(f"{eng.num_comments}cmt")
                if parts:
                    eng_str = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf_str = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""

            lines.append(f"**{item.id}** (score:{item.score}) r/{item.subreddit}{date_str}{conf_str}{eng_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")

            if item.comment_insights:
                lines.append("  Insights:")
                for insight in item.comment_insights[:3]:
                    lines.append(f"    - {insight}")
            lines.append("")


def _render_x_section(lines: list, report: schema.Report, limit: int):
    """Render X section."""
    if report.x_error:
        lines.append("### X Posts")
        lines.append("")
        lines.append(f"**ERROR:** {report.x_error}")
        lines.append("")
    elif report.x:
        lines.append("### X Posts")
        lines.append("")
        for item in report.x[:limit]:
            eng_str = ""
            if item.engagement:
                eng = item.engagement
                parts = []
                if eng.likes is not None:
                    parts.append(f"{eng.likes}likes")
                if eng.reposts is not None:
                    parts.append(f"{eng.reposts}rt")
                if eng.views is not None:
                    parts.append(f"{_format_count(eng.views)}views")
                if eng.bookmarks is not None:
                    parts.append(f"{eng.bookmarks}saved")
                if parts:
                    eng_str = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf_str = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""
            media_str = " [media]" if item.has_media else ""

            lines.append(f"**{item.id}** (score:{item.score}) @{item.author_handle}{date_str}{conf_str}{eng_str}{media_str}")
            text_preview = item.text[:200] + "..." if len(item.text) > 200 else item.text
            lines.append(f"  {text_preview}")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")


def _render_hn_section(lines: list, report: schema.Report, limit: int):
    """Render HackerNews section."""
    if report.hn_error:
        lines.append("### HackerNews")
        lines.append("")
        lines.append(f"**ERROR:** {report.hn_error}")
        lines.append("")
    elif report.hn:
        lines.append("### HackerNews")
        lines.append("")
        for item in report.hn[:limit]:
            eng_str = ""
            if item.engagement:
                eng = item.engagement
                parts = []
                if eng.points is not None:
                    parts.append(f"{eng.points}pts")
                if eng.num_comments is not None:
                    parts.append(f"{eng.num_comments}cmt")
                if parts:
                    eng_str = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf_str = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""

            lines.append(f"**{item.id}** (score:{item.score}) @{item.author}{date_str}{conf_str}{eng_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append(f"  Discussion: {item.hn_url}")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")


def _render_news_section(lines: list, report: schema.Report, limit: int):
    """Render News section."""
    if report.news_error:
        lines.append("### News")
        lines.append("")
        lines.append(f"**ERROR:** {report.news_error}")
        lines.append("")
    elif report.news:
        lines.append("### News")
        lines.append("")
        for item in report.news[:limit]:
            date_str = f" ({item.date})" if item.date else " (date unknown)"
            source = item.source_name or item.source_domain

            lines.append(f"**{item.id}** (score:{item.score}) {source}{date_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            snippet = item.snippet[:150] + "..." if len(item.snippet) > 150 else item.snippet
            if snippet:
                lines.append(f"  {snippet}")
            lines.append("")


def _render_web_section(lines: list, report: schema.Report, limit: int):
    """Render Web Results section."""
    if report.web_error:
        lines.append("### Web Results")
        lines.append("")
        lines.append(f"**ERROR:** {report.web_error}")
        lines.append("")
    elif report.web:
        lines.append("### Web Results")
        lines.append("")
        for item in report.web[:limit]:
            date_str = f" ({item.date})" if item.date else " (date unknown)"
            schema_tag = " [schema]" if item.has_schema_data else ""

            lines.append(f"**{item.id}** (score:{item.score}) {item.source_domain}{date_str}{schema_tag}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            snippet = item.snippet[:150] + "..." if len(item.snippet) > 150 else item.snippet
            if snippet:
                lines.append(f"  {snippet}")
            if item.extra_snippets:
                for es in item.extra_snippets[:2]:
                    lines.append(f"  > {es[:120]}")
            lines.append("")


def _render_video_section(lines: list, report: schema.Report, limit: int):
    """Render Video section."""
    if report.video_error:
        lines.append("### Videos")
        lines.append("")
        lines.append(f"**ERROR:** {report.video_error}")
        lines.append("")
    elif report.videos:
        lines.append("### Videos")
        lines.append("")
        for item in report.videos[:limit]:
            date_str = f" ({item.date})" if item.date else ""
            creator_str = f" by {item.creator}" if item.creator else ""
            duration_str = f" [{item.duration}]" if item.duration else ""

            lines.append(f"**{item.id}** (score:{item.score}) {item.source_domain}{date_str}{creator_str}{duration_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append("")


def _render_discussion_section(lines: list, report: schema.Report, limit: int):
    """Render Discussions section."""
    if report.discussions:
        lines.append("### Discussions")
        lines.append("")
        for item in report.discussions[:limit]:
            date_str = f" ({item.date})" if item.date else ""

            lines.append(f"**{item.id}** (score:{item.score}) {item.forum_name}{date_str}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            snippet = item.snippet[:150] + "..." if len(item.snippet) > 150 else item.snippet
            if snippet:
                lines.append(f"  {snippet}")
            lines.append("")


def render_context_snippet(report: schema.Report) -> str:
    """Render reusable context snippet."""
    lines = []
    lines.append(f"# Context: {report.topic} (Last 30 Days)")
    lines.append("")
    lines.append(f"*Generated: {report.generated_at[:10]} | Sources: {report.mode}*")
    lines.append("")

    lines.append("## Key Sources")
    lines.append("")

    all_items = []
    for item in report.reddit[:5]:
        all_items.append((item.score, "Reddit", item.title, item.url))
    for item in report.x[:5]:
        all_items.append((item.score, "X", item.text[:50] + "...", item.url))
    for item in report.hn[:3]:
        all_items.append((item.score, "HN", item.title[:50], item.url))
    for item in report.news[:3]:
        all_items.append((item.score, "News", item.title[:50], item.url))
    for item in report.web[:3]:
        all_items.append((item.score, "Web", item.title[:50], item.url))
    for item in report.videos[:2]:
        all_items.append((item.score, "Video", item.title[:50], item.url))
    for item in report.discussions[:2]:
        all_items.append((item.score, "Forum", item.title[:50], item.url))

    all_items.sort(key=lambda x: -x[0])
    for _score, source, text, url in all_items[:10]:
        lines.append(f"- [{source}] {text}")

    lines.append("")

    if report.summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(report.summary[:500])
        lines.append("")

    return "\n".join(lines)


def render_full_report(report: schema.Report) -> str:
    """Render full markdown report."""
    lines = []

    lines.append(f"# {report.topic} - Last 30 Days Research Report")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")
    lines.append(f"**Mode:** {report.mode}")
    lines.append("")

    # Models
    if report.xai_model_used:
        lines.append("## Models Used")
        lines.append("")
        lines.append(f"- **xAI:** {report.xai_model_used}")
        lines.append("")

    # AI Summary
    if report.summary:
        lines.append("## AI Summary")
        lines.append("")
        lines.append(report.summary)
        lines.append("")

    # Infobox
    if report.infobox:
        ib = report.infobox
        lines.append("## Knowledge Panel")
        lines.append("")
        if ib.get("title"):
            lines.append(f"**{ib['title']}**")
        if ib.get("description"):
            lines.append(ib["description"])
        lines.append("")

    # Reddit
    if report.reddit:
        lines.append("## Reddit Threads")
        lines.append("")
        for item in report.reddit:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Subreddit:** r/{item.subreddit}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.why_relevant}")
            if item.engagement:
                eng = item.engagement
                lines.append(f"- **Engagement:** {eng.score or '?'} points, {eng.num_comments or '?'} comments")
            if item.comment_insights:
                lines.append("")
                lines.append("**Key Insights from Comments:**")
                for insight in item.comment_insights:
                    lines.append(f"- {insight}")
            lines.append("")

    # X
    if report.x:
        lines.append("## X Posts")
        lines.append("")
        for item in report.x:
            lines.append(f"### {item.id}: @{item.author_handle}")
            lines.append("")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            if item.engagement:
                eng = item.engagement
                lines.append(f"- **Engagement:** {eng.likes or '?'} likes, {eng.reposts or '?'} reposts")
            lines.append("")
            lines.append(f"> {item.text}")
            lines.append("")

    # HN
    if report.hn:
        lines.append("## HackerNews")
        lines.append("")
        for item in report.hn:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Discussion:** {item.hn_url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Score:** {item.score}/100")
            if item.engagement:
                eng = item.engagement
                lines.append(f"- **Engagement:** {eng.points or '?'} points, {eng.num_comments or '?'} comments")
            lines.append("")

    # News
    if report.news:
        lines.append("## News Articles")
        lines.append("")
        for item in report.news:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Source:** {item.source_name or item.source_domain}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Score:** {item.score}/100")
            if item.snippet:
                lines.append("")
                lines.append(f"> {item.snippet}")
            lines.append("")

    # Web
    if report.web:
        lines.append("## Web Results")
        lines.append("")
        for item in report.web:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Source:** {item.source_domain}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Score:** {item.score}/100")
            if item.snippet:
                lines.append("")
                lines.append(f"> {item.snippet}")
            lines.append("")

    # Videos
    if report.videos:
        lines.append("## Videos")
        lines.append("")
        for item in report.videos:
            creator_str = f" by {item.creator}" if item.creator else ""
            lines.append(f"### {item.id}: {item.title}{creator_str}")
            lines.append("")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Score:** {item.score}/100")
            if item.duration:
                lines.append(f"- **Duration:** {item.duration}")
            lines.append("")

    # Discussions
    if report.discussions:
        lines.append("## Forum Discussions")
        lines.append("")
        for item in report.discussions:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Forum:** {item.forum_name}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'}")
            lines.append(f"- **Score:** {item.score}/100")
            if item.snippet:
                lines.append("")
                lines.append(f"> {item.snippet}")
            lines.append("")

    # FAQ
    if report.faqs:
        lines.append("## Frequently Asked Questions")
        lines.append("")
        for faq in report.faqs:
            lines.append(f"**Q: {faq.get('question', '')}**")
            lines.append(f"A: {faq.get('answer', '')}")
            lines.append("")

    return "\n".join(lines)


def write_outputs(
    report: schema.Report,
    raw_brave_web: Optional[dict] = None,
    raw_brave_reddit: Optional[dict] = None,
    raw_brave_news: Optional[dict] = None,
    raw_brave_video: Optional[dict] = None,
    raw_xai: Optional[dict] = None,
    raw_hn: Optional[dict] = None,
    raw_reddit_enriched: Optional[list] = None,
):
    """Write all output files."""
    ensure_output_dir()

    # report.json
    with open(OUTPUT_DIR / "report.json", 'w') as f:
        json.dump(report.to_dict(), f, indent=2)

    # report.md
    with open(OUTPUT_DIR / "report.md", 'w') as f:
        f.write(render_full_report(report))

    # last30days.context.md
    with open(OUTPUT_DIR / "last30days.context.md", 'w') as f:
        f.write(render_context_snippet(report))

    # Raw responses
    raw_files = {
        "raw_brave_web.json": raw_brave_web,
        "raw_brave_reddit.json": raw_brave_reddit,
        "raw_brave_news.json": raw_brave_news,
        "raw_brave_video.json": raw_brave_video,
        "raw_xai.json": raw_xai,
        "raw_hn.json": raw_hn,
    }

    for filename, data in raw_files.items():
        if data:
            with open(OUTPUT_DIR / filename, 'w') as f:
                json.dump(data, f, indent=2)

    if raw_reddit_enriched:
        with open(OUTPUT_DIR / "raw_reddit_threads_enriched.json", 'w') as f:
            json.dump(raw_reddit_enriched, f, indent=2)


def get_context_path() -> str:
    """Get path to context file."""
    return str(OUTPUT_DIR / "last30days.context.md")
