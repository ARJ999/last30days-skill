# /last30days

**The AI world reinvents itself every month. This Claude Code skill keeps you current.** /last30days researches your topic across 7 sources — Reddit, X/Twitter, HackerNews, News, Web, Videos, and Forum Discussions — finds what the community is actually upvoting and sharing, and writes you a prompt that works today, not six months ago.

**Best for prompt research**: discover what prompting techniques actually work for any tool (ChatGPT, Midjourney, Claude, Figma AI, etc.) by learning from real community discussions and best practices.

**But also great for anything trending**: music, culture, news, product recommendations, viral trends, or any question where "what are people saying right now?" matters.

## Installation

```bash
# Clone the repo
git clone https://github.com/mvanhorn/last30days-skill.git ~/.claude/skills/last30days

# Add your API keys
mkdir -p ~/.config/last30days
cat > ~/.config/last30days/.env << 'EOF'
OPENROUTER_API_KEY=your-openrouter-api-key
XAI_API_KEY=your-xai-api-key
EOF
chmod 600 ~/.config/last30days/.env
```

### Getting API Keys

| Key | Source | What It Unlocks |
|-----|--------|----------------|
| `OPENROUTER_API_KEY` | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Reddit, News, Web, Videos, Discussions, AI Summary via Perplexity |
| `XAI_API_KEY` | [console.x.ai](https://console.x.ai) | X/Twitter posts with full engagement metrics |

Both keys are **optional** — the skill always works with HackerNews (free, no key needed).

## Usage

```
/last30days [topic]
/last30days [topic] for [tool]
```

Examples:
- `/last30days prompting techniques for ChatGPT for legal questions`
- `/last30days iOS app mockups for Nano Banana Pro`
- `/last30days What are the best rap songs lately`
- `/last30days remotion animations for Claude Code`
- `/last30days top claude code skills`

## What It Does

1. **Researches** — Searches 7 sources in parallel: Reddit, X/Twitter, HackerNews, News, Web, Videos, and Forum Discussions from the last 30 days
2. **Scores** — Ranks results using engagement-aware scoring (upvotes, likes, reposts, views, bookmarks, points, comments)
3. **Synthesizes** — Identifies patterns, best practices, and what the community actually recommends
4. **Delivers** — Either writes copy-paste-ready prompts for your target tool, or gives you a curated expert-level answer

## Operating Modes

The skill adapts to your available API keys:

| Mode | Keys Required | Sources |
|------|--------------|---------|
| **Full** | `OPENROUTER_API_KEY` + `XAI_API_KEY` | All 7 sources + AI Summary |
| **Perplexity** | `OPENROUTER_API_KEY` only | Reddit, HN, News, Web, Videos, Discussions (6 sources) |
| **X** | `XAI_API_KEY` only | X/Twitter + HN (2 sources) |
| **HN-Only** | None | HackerNews only (free, always available) |

## Architecture

Zero external Python dependencies. Uses only Python stdlib (`urllib`, `json`, `hashlib`, `concurrent.futures`, `dataclasses`).

### Sources & APIs

**Perplexity API** (via OpenRouter) powers 6 of 7 sources:
- **Reddit** — `sonar-pro-search` with `search_domain_filter=["reddit.com"]`, enriched with real thread engagement (score, upvote_ratio, num_comments, top comment excerpts, comment insights)
- **News** — `sonar-pro-search` with `search_recency_filter` for time-sensitive results
- **Web** — `sonar-pro-search` for general web search with citations and extra snippets
- **Videos** — `sonar-pro-search` with `search_domain_filter` targeting video platforms; in `--deep` mode, also uses `sonar-deep-research` for comprehensive video discovery
- **Discussions** — `sonar-pro-search` with `search_domain_filter` targeting Stack Overflow, Discourse, etc.
- **AI Summary** — `sonar-deep-research` for comprehensive AI summary with inline web citations and follow-up questions

Perplexity features used: `search_domain_filter` (per-source site scoping), `search_recency_filter` (date range), `search_after_date_filter`/`search_before_date_filter` (MM/DD/YYYY date bounds), `search_context_size` ("high" for sonar-pro-search, not used for deep-research).

**xAI API** (Responses API) powers X/Twitter search:
- Uses `x_search` agent tool with native `from_date`/`to_date` date filtering (ISO 8601)
- Returns full engagement metrics: likes, reposts, replies, quotes, views, bookmarks
- Media detection: `has_media` flag, `enable_image_understanding` for analyzing images in posts
- Preferred model: `grok-4-1-fast-reasoning` (chain-of-thought reasoning + agentic tool calling)

**HackerNews Algolia API** — free, no authentication:
- Returns stories with verified points and comment counts
- Always available as baseline

### Processing Pipeline

```
env.py → models.py → parallel search (9 threads) → reddit_enrich.py
    → normalize.py → score.py → dedupe.py → render.py
```

1. **Environment** — Load API keys from `~/.config/last30days/.env` (env vars override)
2. **Models** — Auto-select best xAI model (prefers `grok-4-1-fast-reasoning`, daily cache)
3. **Search** — Run up to 7 source searches in parallel via `concurrent.futures`
4. **Enrich** — Fetch real Reddit thread JSON for engagement metrics
5. **Normalize** — Convert raw API responses to canonical schema (7 normalizers)
6. **Score** — Popularity-aware ranking with source-specific weight formulas
7. **Deduplicate** — Per-source text dedup + cross-source URL dedup (priority: Reddit > X > HN > News > Discussions > Web > Videos)
8. **Render** — Generate output in compact, markdown, JSON, or context format

### Engagement Verification

The `engagement_verified` flag distinguishes sources with real engagement data:
- **Reddit**: Verified after enrichment (fetches actual score, upvote_ratio, num_comments from Reddit JSON)
- **X/Twitter**: Verified when xAI returns likes or reposts data
- **HN**: Always verified (Algolia returns real points and comments)
- **News/Web/Videos/Discussions**: Never verified (no engagement data from Perplexity)

Scoring impact: +8 points for verified, -15 for unknown/missing engagement.

### Scoring

| Source | Relevance | Recency | Engagement | Notes |
|--------|-----------|---------|------------|-------|
| Reddit | 40% | 25% | 35% | 45% score + 30% upvote_ratio + 25% comments |
| X | 40% | 25% | 35% | 30% reposts + 25% likes + 20% views + 10% replies + 10% quotes + 5% bookmarks |
| HN | 40% | 25% | 35% | 60% points + 40% comments |
| News | 45% | 55% | — | Time-sensitive, no engagement |
| Web | 55% | 45% | — | -10pt source penalty, +5 citation, +3 extra_snippets |
| Videos | 50% | 50% | — | Balanced |
| Discussions | 45% | 25% | 30% | Engagement proxy: `min(100, snippet_count × 20)` |

Engagement values use `log1p()` for logarithmic scaling. Min-max normalized to 0-100 within batch.

Date confidence adjustments: +5 (high), -5 (medium), -20 (low/no date).

### Data Quality

Each report includes transparency metrics:
- Total items and sources used/failed
- Verified dates and engagement percentages
- Average item recency in days
- AI Summary availability

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

### Embedding in Other Skills

```markdown
## Recent Research Context
!python3 ~/.claude/skills/last30days/scripts/last30days.py "your topic" --emit=context
```

```bash
# JSON for programmatic use
python3 ~/.claude/skills/last30days/scripts/last30days.py "topic" --emit=json > research.json

# Get output path
CONTEXT_PATH=$(python3 ~/.claude/skills/last30days/scripts/last30days.py "topic" --emit=path)
cat "$CONTEXT_PATH"
```

## Output Files

All outputs are written to `~/.local/share/last30days/out/`:

| File | Description |
|------|-------------|
| `report.md` | Human-readable full report |
| `report.json` | Normalized data with scores |
| `last30days.context.md` | Compact reusable snippet for other skills |
| `raw_perplexity_web.json` | Raw Perplexity Web search response |
| `raw_perplexity_reddit.json` | Raw Perplexity Reddit search response |
| `raw_perplexity_news.json` | Raw Perplexity News search response |
| `raw_perplexity_video.json` | Raw Perplexity Video search response |
| `raw_perplexity_deep.json` | Raw Perplexity deep research response |
| `raw_perplexity_discussions.json` | Raw Perplexity Discussions search response |
| `raw_xai.json` | Raw xAI API response |
| `raw_hn.json` | Raw HN Algolia API response |
| `raw_reddit_threads_enriched.json` | Enriched Reddit thread data |

## Configuration

Config file: `~/.config/last30days/.env`

```env
# Required for full research (Reddit, News, Web, Videos, Discussions, AI Summary)
OPENROUTER_API_KEY=your-openrouter-api-key

# Required for X/Twitter research
XAI_API_KEY=your-xai-api-key

# Optional: xAI model selection
XAI_MODEL_POLICY=latest        # latest (auto) or stable
XAI_MODEL_PIN=grok-4-1-fast-reasoning    # Pin to specific model
```

Environment variables override `.env` file values.

## Project Structure

```
last30days-skill/
├── SKILL.md                    # Claude Code skill interface
├── SPEC.md                     # Technical specification
├── CLAUDE.md                   # Project instructions
├── README.md                   # This file
├── scripts/
│   ├── last30days.py           # CLI orchestrator
│   └── lib/
│       ├── env.py              # Config & API key loading
│       ├── dates.py            # Date range & recency scoring
│       ├── cache.py            # 24-hour TTL caching
│       ├── http.py             # stdlib HTTP client with retry
│       ├── models.py           # xAI model auto-selection
│       ├── schema.py           # Dataclass schemas (7 item types + Report)
│       ├── openrouter_client.py # OpenRouter API client (auth, rate limit, errors)
│       ├── perplexity_web.py   # Web search (sonar-pro-search) + deep research (sonar-deep-research)
│       ├── perplexity_reddit.py # Reddit search via search_domain_filter
│       ├── perplexity_news.py  # News search with recency filter
│       ├── perplexity_video.py # Video search via search_domain_filter
│       ├── perplexity_discussions.py # Discussions search via search_domain_filter
│       ├── xai_x.py            # xAI Responses API + x_search tool
│       ├── hn.py               # HackerNews Algolia API
│       ├── reddit_enrich.py    # Reddit thread JSON enrichment (score, ratio, comments, insights)
│       ├── normalize.py        # Raw API → canonical schema (7 normalizers)
│       ├── score.py            # Engagement-aware scoring
│       ├── dedupe.py           # Text + URL deduplication
│       ├── render.py           # Output rendering (compact/md/json/context)
│       └── ui.py               # Terminal progress display
├── fixtures/                   # Mock data for --mock mode
│   ├── perplexity_web_items_sample.json
│   ├── perplexity_reddit_sample.json
│   ├── perplexity_news_sample.json
│   ├── perplexity_video_sample.json
│   ├── perplexity_deep_research_sample.json
│   ├── perplexity_discussions_sample.json
│   ├── xai_sample.json
│   ├── hn_sample.json
│   ├── reddit_thread_sample.json
│   └── models_xai_sample.json
├── tests/                      # Unit tests
│   ├── test_dates.py
│   ├── test_cache.py
│   ├── test_models.py
│   ├── test_score.py
│   ├── test_dedupe.py
│   ├── test_normalize.py
│   └── test_render.py
└── plans/                      # Architecture documents
    └── revamp-brave-xai-architecture.md
```

## Dependencies

Zero external Python dependencies. Uses only Python stdlib:
- `urllib.request`, `urllib.parse`, `urllib.error` — HTTP
- `json` — Serialization
- `hashlib` — Cache keys
- `concurrent.futures` — Parallel execution (up to 9 threads)
- `dataclasses` — Schema definitions
- `datetime`, `time` — Date handling
- `pathlib` — File paths
- `threading` — UI spinners
- `gzip` — Response decompression
- `re` — Pattern matching

---

## Examples

### Legal Prompting (Hallucination Prevention)

**Query:** `/last30days prompting techniques for chatgpt for legal questions`

**Research Output:**
> The dominant theme is hallucination prevention - multiple sources discuss lawyers being fined or embarrassed for submitting fake case citations that ChatGPT fabricated. Key prompting strategies include: (1) using Deep Research mode or grounding tools with uploaded primary sources, (2) building "Hallucination Prevention Systems" into prompts that force epistemic honesty, (3) prompting for procedural questions rather than case law lookups, and (4) framing outputs as "issue-spotting" rather than legal advice.

**Key patterns discovered:**
1. Hallucination prevention clauses - "If you don't know a case citation, say so rather than inventing one"
2. Role assignment - assign ChatGPT a specific persona (paralegal, issue-spotter) to constrain outputs
3. Structured output requirements - request specific sections (risks, key terms, questions for counsel)
4. Epistemic humility enforcement - "acknowledge uncertainty" and "flag when you're unsure"
5. Scope limitation - focus on procedural questions, not case law research

---

### iOS App Mockup (Nano Banana Pro)

**Query:** `/last30days prompting tips for nano banana pro for ios designs`

**Research Output:**
> The community has converged on JSON-structured prompts for UI work. The key workflow: take an existing image, have Gemini generate a JSON prompt from it, then iterate. For iOS specifically, users documented using Nano Banana Pro for iOS app mockup designs in "vibe coding" workflows.

**Generated Prompt:**

```json
{
  "image_type": "UI mockup",
  "device": {
    "frame": "iPhone 16 Pro",
    "display": "realistic screen with subtle reflection",
    "orientation": "portrait"
  },
  "app_concept": "SwimMom - fitness and community app for mothers who swim",
  "screen": "home dashboard",
  "design_system": {
    "style": "iOS 18 native",
    "corners": "rounded, 16px radius",
    "shadows": "soft drop shadows, subtle depth",
    "spacing": "8pt grid, generous whitespace"
  }
}
```

**The Result:**

<p align="center">
  <img src="assets/swimmom-mockup.jpeg" width="400" alt="SwimMom iOS app mockup"/>
</p>

---

### Photorealistic Portraits (Aging Grid)

**Query:** `/last30days photorealistic people in nano banana pro`

**Generated Prompt:**

```json
{
  "prompt_type": "Ultra-Photorealistic Multi-Panel Portrait",
  "layout": "2x2 grid, seamless white dividers",
  "consistency": {
    "same_person": true,
    "preserve_features": ["bone structure", "freckle pattern", "eye shape", "heterochromia"]
  },
  "subject": {
    "identity": "Same woman shown at 4 life stages",
    "distinctive_features": {
      "eyes": "Almond-shaped cat eyes with heterochromia - one green, one amber",
      "skin": "Fair complexion densely covered in natural freckles"
    }
  }
}
```

**The Result:**

<p align="center">
  <img src="assets/aging-portrait.jpeg" width="500" alt="Aging portrait grid - same woman at 10, 20, 40, and 80"/>
</p>

---

### Discover Viral Trends (Dog as Human)

**Query:** `/last30days using ChatGPT to make images of dogs`

**Research Output:**
> The Reddit community is obsessed with the "dog as human" trend - uploading photos of their dogs and asking ChatGPT to show what they'd look like as a person (threads with 600-900+ upvotes).

<p align="center">
  <img src="assets/dog-original.jpeg" width="300" alt="Original dog photo"/>
  &nbsp;&nbsp;->&nbsp;&nbsp;
  <img src="assets/dog-as-human.png" width="300" alt="Dog as human"/>
</p>

Same golden fur -> red hair. Same tongue out. Same harness. ChatGPT nailed it.

---

### Suno AI Music (Simple Mode)

**Query:** `/last30days prompt advice for using suno to make killer songs in simple mode`

**Key patterns discovered:**
1. Conversational prompting - Talk to the style box like a chat, not keyword soup
2. Bracket structure tags - Use `[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Outro]` in lyrics
3. Less is more - 5 or fewer focused style tags outperform over-tagging
4. Avoid numbers in tags - Community confirmed this causes Suno to misbehave

**The Result:** A complete rap song about self-aware AI that loves Claude Code.

---

### Use it for:
- **Prompt research** - "What prompting techniques work for legal questions in ChatGPT?"
- **Tool best practices** - "How are people using Remotion with Claude Code?"
- **Trend discovery** - "What are the best rap songs right now?"
- **Product research** - "What do people think of the new M4 MacBook?"
- **Viral content** - "What's the dog-as-human trend on ChatGPT?"
- **Setup guides** - "How to best setup clawdbot"
- **Developer workflows** - "How do I use Codex with Claude Code"

---

*30 days of research. 30 seconds of work.*

*Prompt research. Trend discovery. Expert answers.*
