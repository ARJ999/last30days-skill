# last30days Skill Specification

## Overview

`last30days` is a Claude Code skill that researches a given topic across 7 sources: Reddit (via Brave Search), X/Twitter (via xAI), HackerNews (via Algolia), News, Web, Videos, and Forum Discussions (via Brave Search). It enforces a strict 30-day recency window, popularity-aware ranking, and produces actionable outputs.

The skill operates in four modes depending on available API keys:
- **Full** (BRAVE_API_KEY + XAI_API_KEY): All 7 sources with AI summary
- **Brave** (BRAVE_API_KEY only): Reddit, HN, News, Web, Videos, Discussions (6 sources)
- **X** (XAI_API_KEY only): X + HN only
- **HN-Only** (no keys): HackerNews only (free, always available)

## Architecture

The orchestrator (`last30days.py`) coordinates discovery, enrichment, normalization, scoring, deduplication, and rendering. Each concern is isolated in `scripts/lib/`:

### Core Infrastructure
- **env.py**: Load and validate API keys from `~/.config/last30days/.env`
- **dates.py**: Date range calculation, recency scoring, and date confidence
- **cache.py**: 24-hour TTL caching keyed by topic + date range + source mode
- **http.py**: stdlib-only HTTP client with retry logic
- **models.py**: xAI model auto-selection with 7-day caching
- **schema.py**: Dataclass schemas for all 7 item types + Report + DataQuality

### Source Modules (Brave Search API)
- **brave_client.py**: Shared Brave API HTTP client with auth, rate limiting, error mapping
- **brave_web.py**: General web search + discussions + FAQ + infobox + summarizer key
- **brave_reddit.py**: Reddit discovery via `site:reddit.com` operator
- **brave_news.py**: News search using dedicated `/news/search` endpoint
- **brave_video.py**: Video search using dedicated `/videos/search` endpoint
- **brave_summarizer.py**: Two-step AI summarizer (free, not billed separately)

### Source Modules (Other APIs)
- **xai_x.py**: xAI Responses API + x_search for X/Twitter
- **hn.py**: HackerNews Algolia API (free, no auth required)
- **reddit_enrich.py**: Fetch Reddit thread JSON for real engagement metrics

### Processing Pipeline
- **normalize.py**: Convert raw API responses to canonical schema (7 normalizers)
- **score.py**: Popularity-aware scoring (source-specific weight formulas)
- **dedupe.py**: Per-source text dedup + cross-source URL dedup with priority ordering
- **render.py**: Generate compact/markdown/JSON/context outputs
- **ui.py**: Terminal progress display with spinners and color-coded source status

## Source Strategy

### Brave Search API (Pro Data AI Plan)
- **Web Search**: `GET /res/v1/web/search` with `freshness`, `extra_snippets`, `summary`, `result_filter`
- **News Search**: `GET /res/v1/news/search` with `freshness`, `count` up to 50
- **Video Search**: `GET /res/v1/videos/search` with `freshness`
- **Summarizer**: `GET /res/v1/summarizer/search` with `key` from web search (free)
- **Reddit**: Web search with `site:reddit.com` operator + custom goggles
- **Discussions**: Extracted from web search `result_filter=discussions`
- **FAQ/Infobox**: Extracted from web search `result_filter=faq,infobox`

### xAI API (X/Twitter)
- Uses Responses API with `x_search` agent tool
- Returns posts with real engagement: likes, reposts, replies, quotes
- Sole source for X/Twitter data (no alternative)

### HackerNews Algolia API
- Free, no authentication required
- Returns stories with verified points and comment counts
- Always available as baseline

## Scoring Formulas

### Reddit / X / HN (engagement-verified sources)
- **40%** relevance + **25%** recency + **35%** engagement
- Engagement normalized to 0-100 within batch using min-max scaling
- +8 points for verified engagement, -15 for unknown

### News (time-sensitive, no engagement)
- **45%** relevance + **55%** recency

### Web (relevance-focused, no engagement)
- **55%** relevance + **45%** recency - **10pt** source penalty
- +5 for schema data, +3 for extra_snippets

### Videos (balanced, no engagement)
- **50%** relevance + **50%** recency

### Discussions (engagement-proxy from snippets)
- **45%** relevance + **25%** recency + **30%** engagement-proxy
- Engagement proxy derived from extra_snippets count

### Date Confidence Adjustments
- High confidence: +5 points
- Medium confidence: -5 points
- Low/no date: -20 points

## Cross-Source Deduplication

Priority order: Reddit > X > HN > News > Discussions > Web > Videos

When the same URL appears in multiple sources, only the highest-priority source keeps it. This ensures engagement-rich versions (Reddit with upvotes) win over plain web results.

## Embedding in Other Skills

### Inline Context Injection
```markdown
## Recent Research Context
!python3 ~/.claude/skills/last30days/scripts/last30days.py "your topic" --emit=context
```

### Read from File
```markdown
## Research Context
!cat ~/.local/share/last30days/out/last30days.context.md
```

### Get Path for Dynamic Loading
```bash
CONTEXT_PATH=$(python3 ~/.claude/skills/last30days/scripts/last30days.py "topic" --emit=path)
cat "$CONTEXT_PATH"
```

### JSON for Programmatic Use
```bash
python3 ~/.claude/skills/last30days/scripts/last30days.py "topic" --emit=json > research.json
```

## CLI Reference

```
python3 ~/.claude/skills/last30days/scripts/last30days.py <topic> [options]

Options:
  --refresh           Bypass cache and fetch fresh data
  --mock              Use fixtures instead of real API calls
  --emit=MODE         Output mode: compact|json|md|context|path (default: compact)
  --sources=MODE      Source selection: auto|all|reddit|x|news|web (default: auto)
  --quick             Faster research, fewer sources per query
  --deep              Comprehensive research with more pages
  --debug             Enable verbose debug logging
```

## Output Files

All outputs are written to `~/.local/share/last30days/out/`:

- `report.md` - Human-readable full report with all 7 sources
- `report.json` - Normalized data with scores for all sources
- `last30days.context.md` - Compact reusable snippet for other skills
- `raw_brave_web.json` - Raw Brave Web Search API response
- `raw_brave_reddit.json` - Raw Brave Reddit search response
- `raw_brave_news.json` - Raw Brave News Search API response
- `raw_brave_video.json` - Raw Brave Video Search API response
- `raw_xai.json` - Raw xAI API response
- `raw_hn.json` - Raw HN Algolia API response
- `raw_reddit_threads_enriched.json` - Enriched Reddit thread data with engagement

## Dependencies

Zero external Python dependencies. Uses only Python stdlib:
- `urllib.request`, `urllib.parse`, `urllib.error` - HTTP
- `json` - Serialization
- `hashlib` - Cache keys
- `concurrent.futures` - Parallel execution (up to 6 threads)
- `dataclasses` - Schema definitions
- `datetime`, `time` - Date handling
- `pathlib` - File paths
- `threading` - UI spinners
- `gzip` - Response decompression
- `re` - Pattern matching

## Configuration

Config file: `~/.config/last30days/.env`

```env
# Required for full research capability
BRAVE_API_KEY=your-brave-search-api-key

# Required for X/Twitter research
XAI_API_KEY=your-xai-api-key

# Optional: xAI model selection
XAI_MODEL_POLICY=latest    # latest (auto) or stable
XAI_MODEL_PIN=grok-4-1     # Pin to specific model
```

Environment variables override `.env` file values.
