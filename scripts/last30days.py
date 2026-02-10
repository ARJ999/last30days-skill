#!/usr/bin/env python3
"""
last30days - Research a topic from the last 30 days across 7 sources.

Sources: Reddit (Perplexity), X (xAI), HackerNews (Algolia), News (Perplexity),
         Web (Perplexity), Videos (Perplexity), Discussions (Perplexity)

Usage:
    python3 last30days.py <topic> [options]

Options:
    --mock              Use fixtures instead of real API calls
    --emit=MODE         Output mode: compact|json|md|context|path (default: compact)
    --sources=MODE      Source selection: auto|all|reddit|x|news|web (default: auto)
    --quick             Faster research with fewer sources
    --deep              Comprehensive research with more sources
    --refresh           Force fresh data (ignore cache)
    --debug             Enable verbose debug logging
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from lib import (
    cache,
    dates,
    dedupe,
    env,
    hn,
    http,
    models,
    normalize,
    openrouter_client,
    perplexity_discussions,
    perplexity_news,
    perplexity_reddit,
    perplexity_video,
    perplexity_web,
    reddit_enrich,
    render,
    schema,
    score,
    ui,
    xai_x,
)


def load_fixture(name: str) -> dict:
    """Load a fixture file."""
    fixture_path = SCRIPT_DIR.parent / "fixtures" / name
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {}


def _search_perplexity_web(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search for web results via Perplexity sonar-pro-search."""
    if mock:
        return load_fixture("perplexity_web_items_sample.json"), None
    try:
        raw = perplexity_web.search_web_items(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity Web error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_perplexity_deep(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Run deep research via Perplexity sonar-deep-research for AI summary."""
    if mock:
        return load_fixture("perplexity_deep_research_sample.json"), None
    try:
        raw = perplexity_web.search_web_deep(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity Deep Research error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_perplexity_reddit(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search for Reddit threads via Perplexity."""
    if mock:
        return load_fixture("perplexity_reddit_sample.json"), None
    try:
        raw = perplexity_reddit.search_reddit(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity Reddit error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_perplexity_news(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search for news via Perplexity."""
    if mock:
        return load_fixture("perplexity_news_sample.json"), None
    try:
        raw = perplexity_news.search_news(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity News error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_perplexity_video(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search for videos via Perplexity."""
    if mock:
        return load_fixture("perplexity_video_sample.json"), None
    try:
        raw = perplexity_video.search_videos(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity Video error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_perplexity_video_deep(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Deep research for video discovery via sonar-deep-research (deep mode only)."""
    if mock:
        return load_fixture("perplexity_video_deep_sample.json"), None
    try:
        raw = perplexity_video.search_videos_deep(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity Video Deep Research error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_perplexity_discussions(
    client: openrouter_client.OpenRouterClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search for discussions via Perplexity."""
    if mock:
        return load_fixture("perplexity_discussions_sample.json"), None
    try:
        raw = perplexity_discussions.search_discussions(client, topic, from_date, to_date, depth=depth)
        return raw, None
    except openrouter_client.OpenRouterError as e:
        return None, f"Perplexity Discussions error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_x(
    topic: str,
    config: dict,
    selected_models: dict,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search X via xAI."""
    if mock:
        return load_fixture("xai_sample.json"), None
    try:
        raw = xai_x.search_x(
            config["XAI_API_KEY"],
            selected_models["xai"],
            topic,
            from_date,
            to_date,
            depth=depth,
        )
        return raw, None
    except http.HTTPError as e:
        return None, f"xAI API error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _search_hn(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search HackerNews via Algolia."""
    if mock:
        return load_fixture("hn_sample.json"), None
    try:
        raw = hn.search_hn(topic, from_date, to_date, depth=depth)
        return raw, None
    except http.HTTPError as e:
        return None, f"HN API error: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def run_research(
    topic: str,
    resolved_sources: str,
    config: dict,
    selected_models: dict,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock: bool = False,
    progress: ui.ProgressDisplay = None,
) -> dict:
    """Run the full research pipeline.

    Returns dict with all raw responses, parsed items, and errors.
    """
    has_openrouter = bool(config.get("OPENROUTER_API_KEY")) or mock
    has_xai = bool(config.get("XAI_API_KEY")) or mock

    or_client = None
    if has_openrouter and not mock:
        or_client = openrouter_client.OpenRouterClient(config["OPENROUTER_API_KEY"])

    # Determine which searches to run based on resolved sources
    run_web = has_openrouter and resolved_sources in ("full", "perplexity", "web")
    run_deep = has_openrouter and resolved_sources in ("full", "perplexity", "web")
    run_reddit = has_openrouter and resolved_sources in ("full", "perplexity", "reddit")
    run_news = has_openrouter and resolved_sources in ("full", "perplexity", "news")
    run_video = has_openrouter and resolved_sources in ("full", "perplexity")
    run_video_deep = run_video and depth == "deep"
    run_discussions = has_openrouter and resolved_sources in ("full", "perplexity")
    run_x = has_xai and resolved_sources in ("full", "x")
    run_hn = True  # HN is always free

    # Raw responses
    raw = {
        "perplexity_web": None, "perplexity_deep": None,
        "perplexity_reddit": None, "perplexity_news": None,
        "perplexity_video": None, "perplexity_video_deep": None,
        "perplexity_discussions": None,
        "xai": None, "hn": None,
    }
    errors = {
        "reddit": None, "x": None, "hn": None,
        "news": None, "web": None, "video": None, "video_deep": None,
        "discussions": None, "deep": None,
    }

    # Phase 1: Parallel search (up to 9 threads: 7 sources + deep research + video deep)
    futures = {}
    with ThreadPoolExecutor(max_workers=9) as executor:
        if run_web:
            if progress:
                progress.start_web()
            futures["perplexity_web"] = executor.submit(
                _search_perplexity_web, or_client, topic, from_date, to_date, depth, mock
            )

        if run_deep:
            futures["perplexity_deep"] = executor.submit(
                _search_perplexity_deep, or_client, topic, from_date, to_date, depth, mock
            )

        if run_reddit:
            if progress:
                progress.start_reddit()
            futures["perplexity_reddit"] = executor.submit(
                _search_perplexity_reddit, or_client, topic, from_date, to_date, depth, mock
            )

        if run_news:
            if progress:
                progress.start_news()
            futures["perplexity_news"] = executor.submit(
                _search_perplexity_news, or_client, topic, from_date, to_date, depth, mock
            )

        if run_video:
            if progress:
                progress.start_videos()
            futures["perplexity_video"] = executor.submit(
                _search_perplexity_video, or_client, topic, from_date, to_date, depth, mock
            )

        if run_video_deep:
            futures["perplexity_video_deep"] = executor.submit(
                _search_perplexity_video_deep, or_client, topic, from_date, to_date, depth, mock
            )

        if run_discussions:
            futures["perplexity_discussions"] = executor.submit(
                _search_perplexity_discussions, or_client, topic, from_date, to_date, depth, mock
            )

        if run_x:
            if progress:
                progress.start_x()
            futures["xai"] = executor.submit(
                _search_x, topic, config, selected_models, from_date, to_date, depth, mock
            )

        if run_hn:
            if progress:
                progress.start_hn()
            futures["hn"] = executor.submit(
                _search_hn, topic, from_date, to_date, depth, mock
            )

        # Collect results
        for key, future in futures.items():
            try:
                result, error = future.result()
                raw[key] = result
                if error:
                    err_key = {
                        "perplexity_web": "web", "perplexity_deep": "deep",
                        "perplexity_reddit": "reddit", "perplexity_news": "news",
                        "perplexity_video": "video", "perplexity_video_deep": "video_deep",
                        "perplexity_discussions": "discussions",
                        "xai": "x", "hn": "hn",
                    }.get(key, key)
                    errors[err_key] = error
                    if progress:
                        progress.show_error(error)
            except Exception as e:
                err_key = {
                    "perplexity_web": "web", "perplexity_deep": "deep",
                    "perplexity_reddit": "reddit", "perplexity_news": "news",
                    "perplexity_video": "video", "perplexity_video_deep": "video_deep",
                    "perplexity_discussions": "discussions",
                    "xai": "x", "hn": "hn",
                }.get(key, key)
                errors[err_key] = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"{key} error: {e}")

    # Parse results from each source
    web_items_raw = perplexity_web.parse_web_results(raw["perplexity_web"] or {}) if raw["perplexity_web"] else []
    discussion_items_raw = perplexity_discussions.parse_discussion_results(raw["perplexity_discussions"] or {}) if raw["perplexity_discussions"] else []
    if progress and run_web:
        progress.end_web(len(web_items_raw), len(discussion_items_raw))

    reddit_items_raw = perplexity_reddit.parse_reddit_results(raw["perplexity_reddit"] or {}) if raw["perplexity_reddit"] else []
    if progress and run_reddit:
        progress.end_reddit(len(reddit_items_raw))

    news_items_raw = perplexity_news.parse_news_results(raw["perplexity_news"] or {}) if raw["perplexity_news"] else []
    if progress and run_news:
        progress.end_news(len(news_items_raw))

    video_items_raw = perplexity_video.parse_video_results(raw["perplexity_video"] or {}) if raw["perplexity_video"] else []

    # Merge video deep research items (deep mode only)
    if raw.get("perplexity_video_deep"):
        deep_video_items = perplexity_video.parse_video_deep_research(raw["perplexity_video_deep"])
        if deep_video_items:
            existing_urls = {item["url"] for item in video_items_raw}
            for dv_item in deep_video_items:
                if dv_item["url"] not in existing_urls:
                    dv_item["id"] = f"V{len(video_items_raw)+1}"
                    video_items_raw.append(dv_item)
                    existing_urls.add(dv_item["url"])

    if progress and run_video:
        progress.end_videos(len(video_items_raw))

    x_items_raw = xai_x.parse_x_response(raw["xai"] or {}) if raw["xai"] else []
    if progress and run_x:
        progress.end_x(len(x_items_raw))

    hn_items_raw = hn.parse_hn_response(raw["hn"] or {}) if raw["hn"] else []
    if progress and run_hn:
        progress.end_hn(len(hn_items_raw))

    # Parse deep research for AI summary + supplementary web items
    deep_data = None
    if raw["perplexity_deep"]:
        deep_data = perplexity_web.parse_deep_research(raw["perplexity_deep"])
        # Merge deep research citation items into web items (avoid duplicates)
        if deep_data.get("web_items"):
            existing_urls = {item["url"] for item in web_items_raw}
            for deep_item in deep_data["web_items"]:
                if deep_item["url"] not in existing_urls:
                    deep_item["id"] = f"W{len(web_items_raw)+1}"
                    web_items_raw.append(deep_item)
                    existing_urls.add(deep_item["url"])

    # Phase 2: Enrichment (Reddit threads)
    raw_reddit_enriched = []

    if reddit_items_raw:
        if progress:
            progress.start_reddit_enrich(1, len(reddit_items_raw))

        def enrich_item(args):
            i, item = args
            try:
                if mock:
                    mock_thread = load_fixture("reddit_thread_sample.json")
                    return i, reddit_enrich.enrich_reddit_item(item, mock_thread), None
                else:
                    return i, reddit_enrich.enrich_reddit_item(item), None
            except Exception as e:
                return i, item, str(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            enrich_futures = {
                executor.submit(enrich_item, (i, item)): i
                for i, item in enumerate(reddit_items_raw)
            }

            completed = 0
            for future in as_completed(enrich_futures):
                i, enriched_item, error = future.result()
                reddit_items_raw[i] = enriched_item
                completed += 1
                if progress:
                    progress.update_reddit_enrich(completed, len(reddit_items_raw))

        raw_reddit_enriched = list(reddit_items_raw)
        if progress:
            progress.end_reddit_enrich()

    # Build summary data from deep research
    summary_data = None
    if deep_data and deep_data.get("summary"):
        summary_data = {
            "summary": deep_data["summary"],
            "citations": deep_data.get("citations", []),
            "followups": deep_data.get("followups", []),
        }
        if progress:
            progress.end_summarizer(True)

    return {
        "raw": raw,
        "errors": errors,
        "reddit_items": reddit_items_raw,
        "x_items": x_items_raw,
        "hn_items": hn_items_raw,
        "news_items": news_items_raw,
        "web_items": web_items_raw,
        "video_items": video_items_raw,
        "discussion_items": discussion_items_raw,
        "summary_data": summary_data,
        "raw_reddit_enriched": raw_reddit_enriched,
    }


def process_results(
    research: dict,
    from_date: str,
    to_date: str,
    progress: ui.ProgressDisplay = None,
) -> dict:
    """Process raw results: normalize, score, dedupe."""
    if progress:
        progress.start_processing()

    # Normalize all sources
    norm_reddit = normalize.normalize_reddit_items(research["reddit_items"], from_date, to_date)
    norm_x = normalize.normalize_x_items(research["x_items"], from_date, to_date)
    norm_hn = normalize.normalize_hn_items(research["hn_items"], from_date, to_date)
    norm_news = normalize.normalize_news_items(research["news_items"], from_date, to_date)
    norm_web = normalize.normalize_web_items(research["web_items"], from_date, to_date)
    norm_videos = normalize.normalize_video_items(research["video_items"], from_date, to_date)
    norm_discussions = normalize.normalize_discussion_items(research["discussion_items"], from_date, to_date)

    # Hard date filter (safety net)
    filt_reddit = normalize.filter_by_date_range(norm_reddit, from_date, to_date)
    filt_x = normalize.filter_by_date_range(norm_x, from_date, to_date)
    filt_hn = normalize.filter_by_date_range(norm_hn, from_date, to_date)
    filt_news = normalize.filter_by_date_range(norm_news, from_date, to_date)
    filt_web = normalize.filter_by_date_range(norm_web, from_date, to_date)
    filt_videos = normalize.filter_by_date_range(norm_videos, from_date, to_date)
    filt_discussions = normalize.filter_by_date_range(norm_discussions, from_date, to_date)

    # Score all sources
    scored_reddit = score.score_reddit_items(filt_reddit)
    scored_x = score.score_x_items(filt_x)
    scored_hn = score.score_hn_items(filt_hn)
    scored_news = score.score_news_items(filt_news)
    scored_web = score.score_web_items(filt_web)
    scored_videos = score.score_video_items(filt_videos)
    scored_discussions = score.score_discussion_items(filt_discussions)

    # Sort by score
    sorted_reddit = score.sort_items(scored_reddit)
    sorted_x = score.sort_items(scored_x)
    sorted_hn = score.sort_items(scored_hn)
    sorted_news = score.sort_items(scored_news)
    sorted_web = score.sort_items(scored_web)
    sorted_videos = score.sort_items(scored_videos)
    sorted_discussions = score.sort_items(scored_discussions)

    # Per-source dedup (text similarity)
    deduped_reddit = dedupe.dedupe_reddit(sorted_reddit)
    deduped_x = dedupe.dedupe_x(sorted_x)
    deduped_hn = dedupe.dedupe_hn(sorted_hn)
    deduped_news = dedupe.dedupe_news(sorted_news)
    deduped_web = dedupe.dedupe_web(sorted_web)
    deduped_videos = dedupe.dedupe_videos(sorted_videos)
    deduped_discussions = dedupe.dedupe_discussions(sorted_discussions)

    # Cross-source URL dedup
    final_reddit, final_x, final_hn, final_news, final_web, final_videos, final_discussions = \
        dedupe.cross_source_url_dedupe(
            deduped_reddit, deduped_x, deduped_hn,
            deduped_news, deduped_web, deduped_videos, deduped_discussions,
        )

    if progress:
        progress.end_processing()

    return {
        "reddit": final_reddit,
        "x": final_x,
        "hn": final_hn,
        "news": final_news,
        "web": final_web,
        "videos": final_videos,
        "discussions": final_discussions,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Research a topic from the last 30 days across 7 sources"
    )
    parser.add_argument("topic", nargs="?", help="Topic to research")
    parser.add_argument("--mock", action="store_true", help="Use fixtures")
    parser.add_argument(
        "--emit",
        choices=["compact", "json", "md", "context", "path"],
        default="compact",
        help="Output mode",
    )
    parser.add_argument(
        "--sources",
        choices=["auto", "all", "reddit", "x", "news", "web"],
        default="auto",
        help="Source selection",
    )
    parser.add_argument("--quick", action="store_true", help="Faster research")
    parser.add_argument("--deep", action="store_true", help="Comprehensive research")
    parser.add_argument("--refresh", action="store_true", help="Force fresh data (ignore cache)")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Enable debug logging
    if args.debug:
        os.environ["LAST30DAYS_DEBUG"] = "1"
        from lib import http as http_module
        http_module.DEBUG = True

    # Determine depth
    if args.quick and args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)
    elif args.quick:
        depth = "quick"
    elif args.deep:
        depth = "deep"
    else:
        depth = "default"

    if not args.topic:
        print("Error: Please provide a topic to research.", file=sys.stderr)
        print("Usage: python3 last30days.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    # Load config
    config = env.get_config()

    # Check for legacy config
    legacy_msg = env.check_legacy_config(config)
    if legacy_msg:
        print(legacy_msg, file=sys.stderr)

    # Determine available sources
    available = env.get_available_sources(config)

    # Mock mode works without keys
    if args.mock:
        resolved_sources = "full"
    else:
        resolved_sources, warning = env.validate_sources(args.sources, available)
        if warning:
            print(f"Note: {warning}", file=sys.stderr)

    # Get date range
    from_date, to_date = dates.get_date_range(30)

    # Check cache (unless --refresh)
    cache_key = cache.get_cache_key(args.topic, from_date, to_date, resolved_sources)
    if not args.refresh and not args.mock:
        cached_data, cache_age = cache.load_cache_with_age(cache_key)
        if cached_data:
            try:
                report = schema.Report.from_dict(cached_data)
                report.from_cache = True
                report.cache_age_hours = cache_age

                progress = ui.ProgressDisplay(args.topic, show_banner=True)
                progress.show_cached(cache_age)

                output_result(report, args.emit, env.get_missing_keys(config))
                return
            except Exception:
                pass  # Cache corrupt, continue with fresh search

    # Check missing keys for promo
    missing_keys = env.get_missing_keys(config)

    # Initialize progress display
    progress = ui.ProgressDisplay(args.topic, show_banner=True)

    # Show promo for missing keys
    if missing_keys != "none":
        progress.show_promo(missing_keys)

    # Select models (xAI only)
    if args.mock:
        mock_xai_models = load_fixture("models_xai_sample.json").get("data", [])
        selected_models = models.get_models(
            {"XAI_API_KEY": "mock", **config},
            mock_xai_models,
        )
    else:
        selected_models = models.get_models(config)

    # Determine mode string
    mode_map = {
        "full": "full",
        "perplexity": "perplexity",
        "reddit": "reddit-only",
        "x": "x-only",
        "news": "news-only",
        "web": "web-only",
        "hn": "hn-only",
    }
    mode = mode_map.get(resolved_sources, resolved_sources)

    # Run research pipeline
    research = run_research(
        args.topic, resolved_sources, config, selected_models,
        from_date, to_date, depth, args.mock, progress,
    )

    # Process results
    processed = process_results(research, from_date, to_date, progress)

    # Build report
    report = schema.create_report(
        args.topic, from_date, to_date, mode,
        xai_model=selected_models.get("xai"),
    )
    report.reddit = processed["reddit"]
    report.x = processed["x"]
    report.hn = processed["hn"]
    report.news = processed["news"]
    report.web = processed["web"]
    report.videos = processed["videos"]
    report.discussions = processed["discussions"]

    # Attach errors
    report.reddit_error = research["errors"]["reddit"]
    report.x_error = research["errors"]["x"]
    report.hn_error = research["errors"]["hn"]
    report.news_error = research["errors"]["news"]
    report.web_error = research["errors"]["web"]
    report.video_error = research["errors"]["video"]
    report.discussions_error = research["errors"]["discussions"]

    # Attach AI summary from deep research
    if research["summary_data"]:
        report.summary = research["summary_data"].get("summary")
        report.summary_citations = research["summary_data"].get("citations", [])
        report.summary_followups = research["summary_data"].get("followups", [])

    # Compute data quality
    report.data_quality = schema.compute_data_quality(report)

    # Generate context snippet
    report.context_snippet_md = render.render_context_snippet(report)

    # Write outputs
    render.write_outputs(
        report,
        raw_perplexity_web=research["raw"].get("perplexity_web"),
        raw_perplexity_deep=research["raw"].get("perplexity_deep"),
        raw_perplexity_reddit=research["raw"].get("perplexity_reddit"),
        raw_perplexity_news=research["raw"].get("perplexity_news"),
        raw_perplexity_video=research["raw"].get("perplexity_video"),
        raw_perplexity_discussions=research["raw"].get("perplexity_discussions"),
        raw_xai=research["raw"].get("xai"),
        raw_hn=research["raw"].get("hn"),
        raw_reddit_enriched=research["raw_reddit_enriched"],
    )

    # Save to cache
    if not args.mock:
        cache.save_cache(cache_key, report.to_dict())

    # Show completion
    progress.show_complete(
        reddit_count=len(processed["reddit"]),
        x_count=len(processed["x"]),
        hn_count=len(processed["hn"]),
        news_count=len(processed["news"]),
        web_count=len(processed["web"]),
        video_count=len(processed["videos"]),
        discussion_count=len(processed["discussions"]),
    )

    # Output result
    output_result(report, args.emit, missing_keys)


def output_result(
    report: schema.Report,
    emit_mode: str,
    missing_keys: str = "none",
):
    """Output the result based on emit mode."""
    if emit_mode == "compact":
        print(render.render_compact(report, missing_keys=missing_keys))
    elif emit_mode == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif emit_mode == "md":
        print(render.render_full_report(report))
    elif emit_mode == "context":
        print(report.context_snippet_md)
    elif emit_mode == "path":
        print(render.get_context_path())


if __name__ == "__main__":
    main()
