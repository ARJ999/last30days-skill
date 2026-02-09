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
- **models.py**: xAI model auto-selection (prefers grok-4-1-fast-reasoning) with daily caching
- **schema.py**: Dataclass schemas for all 7 item types + Report + DataQuality

### Source Modules (Brave Search API)
- **brave_client.py**: Shared Brave API HTTP client with auth, rate limiting, error mapping
- **brave_web.py**: General web search + discussions + FAQ + infobox + summarizer key + schema extraction + deep results
- **brave_reddit.py**: Reddit discovery via `site:reddit.com` operator with custom goggles
- **brave_news.py**: News search using dedicated `/news/search` endpoint
- **brave_video.py**: Video search using dedicated `/videos/search` endpoint
- **brave_summarizer.py**: Two-step AI summarizer (free, not billed separately)

### Source Modules (Other APIs)
- **xai_x.py**: xAI Responses API + x_search with native date/media params for X/Twitter
- **hn.py**: HackerNews Algolia API (free, no auth required)
- **reddit_enrich.py**: Fetch Reddit thread JSON for real engagement metrics (score, upvote_ratio, num_comments, top_comments with scores, comment_insights extracted via heuristics)

### Processing Pipeline
- **normalize.py**: Convert raw API responses to canonical schema (7 normalizers)
- **score.py**: Popularity-aware scoring (source-specific weight formulas)
- **dedupe.py**: Per-source text dedup + cross-source URL dedup with priority ordering
- **render.py**: Generate compact/markdown/JSON/context outputs
- **ui.py**: Terminal progress display with spinners and color-coded source status

## Source Strategy

### Brave Search API (Pro AI Plan)
- **Web Search**: `GET /res/v1/web/search` with `freshness`, `extra_snippets`, `summary`, `result_filter`, `spellcheck`, `search_lang`, `country`, `goggles` (default goggles: boost GitHub/dev.to/StackOverflow, discard Pinterest)
- **News Search**: `GET /res/v1/news/search` with `freshness`, `count` up to 50, `spellcheck`, `search_lang`, `country`
- **Video Search**: `GET /res/v1/videos/search` with `freshness`, `spellcheck`, `search_lang`, `country`
- **Summarizer**: `GET /res/v1/summarizer/search` with `key` from web search (free, `entity_info` enabled)
- **Reddit**: Web search with `site:reddit.com` operator + custom goggles
- **Discussions**: Extracted from web search `result_filter=discussions`
- **FAQ/Infobox**: Extracted from web search `result_filter=faq,infobox`
- **Schema-Enriched Results**: Extracts `rating`, `review`, `article`, `product`, `book`, `recipe`, `creative_work`, `movie`, `music_recording`, `qa` from web results
- **Deep Results**: Extracts nested `buttons` (sitelinks), `news`, `social`, `videos` from web result `deep_results` field
- **Spellcheck**: Enabled on all endpoints for better results with typos
- **Localization**: Optional `BRAVE_SEARCH_LANG` and `BRAVE_COUNTRY` config

### xAI API (X/Twitter)
- Uses Responses API (`/v1/responses`) with `x_search` agent tool
- Native date filtering: `from_date` and `to_date` passed as tool params (ISO 8601)
- Native image understanding: `enable_image_understanding=true` for analyzing images in posts
- Returns posts with rich engagement: likes, reposts, replies, quotes, views, bookmarks
- Media detection: `has_media` flag for posts containing images/video
- Preferred model: `grok-4-1-fast-reasoning` (chain-of-thought reasoning + agentic tool calling)
- Handle filtering available: `allowed_x_handles` and `excluded_x_handles`
- Sole source for X/Twitter data (no alternative)

### HackerNews Algolia API
- Free, no authentication required
- Returns stories with verified points and comment counts
- Always available as baseline

## Scoring Formulas

### Engagement Verification

The `engagement_verified` flag indicates trustworthy engagement data from the source:
- **Reddit**: `True` after enrichment via `reddit_enrich.py` (fetches real score, upvote_ratio, num_comments from Reddit JSON API). `False` if enrichment fails or thread is deleted.
- **X/Twitter**: `True` if xAI returns at least likes or reposts data. `False` if no engagement data in response.
- **HN**: Always `True` (Algolia API always returns verified points and comment counts).
- **News/Web/Videos/Discussions**: Always `False` (no engagement data available from Brave).

Scoring bonus: +8 points for `engagement_verified=True`, -15 for unknown/missing engagement.

### Engagement Normalization

All engagement raw scores are normalized to 0-100 within their batch using min-max scaling:
```
normalized = (value - min) / (max - min) * 100
```
Default engagement score for items without data: 20.

### Reddit / X / HN (engagement-verified sources)
- **40%** relevance + **25%** recency + **35%** engagement
- X engagement formula: 30% reposts + 25% likes + 20% views + 10% replies + 10% quotes + 5% bookmarks
- Reddit engagement formula: 45% score + 30% upvote_ratio (×10 scale) + 25% comments
- HN engagement formula: 60% points + 40% comments
- All engagement values use `log1p()` for logarithmic scaling (handles wide value ranges)

### News (time-sensitive, no engagement)
- **45%** relevance + **55%** recency

### Web (relevance-focused, no engagement)
- **55%** relevance + **45%** recency - **10pt** source penalty
- +5 for schema data presence (boolean `has_schema_data`)
- +3 for rich schema extraction (rating, review, product, etc.)
- +3 for deep results (sitelinks, nested news/social/videos)
- +3 for extra_snippets (additional text excerpts)

### Videos (balanced, no engagement)
- **50%** relevance + **50%** recency

### Discussions (engagement-proxy from snippets)
- **45%** relevance + **25%** recency + **30%** engagement-proxy
- Engagement proxy formula: `min(100, snippet_count × 20)` (0-5 snippets maps to 0-100)

### Date Confidence Adjustments
- High confidence: +5 points
- Medium confidence: -5 points
- Low/no date: -20 points

## Deduplication

### Per-Source Text Dedup
Uses Jaccard similarity on 3-character ngrams with a 0.7 threshold. When two items are near-duplicates, the higher-scored item is kept.

### Cross-Source URL Dedup
Priority order: Reddit > X > HN > News > Discussions > Web > Videos

URL normalization strips scheme, `www.` prefix, trailing slashes, and query parameters before comparison. When the same URL appears in multiple sources, only the highest-priority source keeps it. This ensures engagement-rich versions (Reddit with upvotes) win over plain web results.

## Data Quality Metrics

Each report includes a `DataQuality` object with transparency metrics:
- **total_items**: Count of all items across all sources
- **verified_dates_count/percent**: Items with high-confidence dates
- **verified_engagement_count/percent**: Items with verified engagement data (Reddit enriched + X + HN)
- **avg_recency_days**: Average age of items in days
- **sources_available**: List of sources that returned data
- **sources_failed**: List of sources that errored
- **has_summary**: Whether Brave AI Summary is available
- **has_infobox**: Whether Knowledge Panel is available
- **faq_count**: Number of FAQ entries from Brave

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
XAI_MODEL_POLICY=latest        # latest (auto) or stable
XAI_MODEL_PIN=grok-4-1-fast-reasoning    # Pin to specific model

# Optional: Brave localization
BRAVE_SEARCH_LANG=en           # Language for search results
BRAVE_COUNTRY=us               # Country for localization
```

Environment variables override `.env` file values.
