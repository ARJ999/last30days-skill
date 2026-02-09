---
name: last30days
description: Research a topic from the last 30 days across Reddit + X + News + Web + Videos + Discussions, become an expert, and write copy-paste-ready prompts for the user's target tool.
argument-hint: "[topic] for [tool]" or "[topic]"
context: fork
agent: Explore
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# last30days: Research Any Topic from the Last 30 Days

Research ANY topic across 7 sources: Reddit, X, HackerNews, News, Web, Videos, and Forum Discussions. Surface what people are actually discussing, recommending, and debating right now.

Use cases:
- **Prompting**: "photorealistic people in Nano Banana Pro", "Midjourney prompts", "ChatGPT image generation" -> learn techniques, get copy-paste prompts
- **Recommendations**: "best Claude Code skills", "top AI tools" -> get a LIST of specific things people mention
- **News**: "what's happening with OpenAI", "latest AI announcements" -> current events and updates
- **General**: any topic you're curious about -> understand what the community is saying

## CRITICAL: Parse User Intent

Before doing anything, parse the user's input for:

1. **TOPIC**: What they want to learn about (e.g., "web app mockups", "Claude Code skills", "image generation")
2. **TARGET TOOL** (if specified): Where they'll use the prompts (e.g., "Nano Banana Pro", "ChatGPT", "Midjourney")
3. **QUERY TYPE**: What kind of research they want:
   - **PROMPTING** - "X prompts", "prompting for X", "X best practices" -> User wants to learn techniques and get copy-paste prompts
   - **RECOMMENDATIONS** - "best X", "top X", "what X should I use", "recommended X" -> User wants a LIST of specific things
   - **NEWS** - "what's happening with X", "X news", "latest on X" -> User wants current events/updates
   - **GENERAL** - anything else -> User wants broad understanding of the topic

Common patterns:
- `[topic] for [tool]` -> "web mockups for Nano Banana Pro" -> TOOL IS SPECIFIED
- `[topic] prompts for [tool]` -> "UI design prompts for Midjourney" -> TOOL IS SPECIFIED
- Just `[topic]` -> "iOS design mockups" -> TOOL NOT SPECIFIED, that's OK
- "best [topic]" or "top [topic]" -> QUERY_TYPE = RECOMMENDATIONS
- "what are the best [topic]" -> QUERY_TYPE = RECOMMENDATIONS

**IMPORTANT: Do NOT ask about target tool before research.**
- If tool is specified in the query, use it
- If tool is NOT specified, run research first, then ask AFTER showing results

**Store these variables:**
- `TOPIC = [extracted topic]`
- `TARGET_TOOL = [extracted tool, or "unknown" if not specified]`
- `QUERY_TYPE = [PROMPTING | RECOMMENDATIONS | NEWS | GENERAL]`

---

## Setup Check

The skill works in four modes based on available API keys:

1. **Full Mode** (BRAVE_API_KEY + XAI_API_KEY): All 7 sources - Reddit, X, HN, News, Web, Videos, Discussions + AI Summary
2. **Brave Mode** (BRAVE_API_KEY only): 6 sources - Reddit, HN, News, Web, Videos, Discussions (no X)
3. **X Mode** (XAI_API_KEY only): X + HN only
4. **HN-Only Mode** (no keys): HackerNews only - still useful, but limited

**API keys are OPTIONAL.** The skill will always work with HN fallback.

### First-Time Setup (Optional but Recommended)

If the user wants to add API keys for better results:

```bash
mkdir -p ~/.config/last30days
cat > ~/.config/last30days/.env << 'ENVEOF'
# last30days API Configuration
# Both keys are optional - skill works with HN-only fallback

# For Reddit, News, Web, Videos, Discussions + AI Summary (Brave Search Pro Data AI)
BRAVE_API_KEY=

# For X/Twitter research (uses xAI's x_search tool)
XAI_API_KEY=
ENVEOF

chmod 600 ~/.config/last30days/.env
echo "Config created at ~/.config/last30days/.env"
echo "Edit to add your API keys for enhanced research."
```

**DO NOT stop if no keys are configured.** Proceed with HN-only mode.

---

## Research Execution

**IMPORTANT: The script handles API key detection and all 7 source searches automatically.** Run it and check the output.

**Step 1: Run the research script**
```bash
python3 ~/.claude/skills/last30days/scripts/last30days.py "$ARGUMENTS" --emit=compact 2>&1
```

The script will automatically:
- Detect available API keys
- Search up to 7 sources in parallel (Reddit via Brave, X via xAI, HN via Algolia, News/Web/Videos/Discussions via Brave)
- Enrich Reddit threads with real engagement data
- Fetch AI summary via Brave Summarizer (free, not billed separately)
- Normalize, score, deduplicate, and rank all results
- Show a promo banner if keys are missing (this is intentional marketing)

**Step 2: Analyze the output**

The script output will indicate the mode and include:
- **Data Quality Metrics** (total items, verified dates %, verified engagement %, avg recency days, sources used/failed)
- **AI Summary** (if available from Brave Summarizer, with inline citations and follow-up questions)
- **Knowledge Panel** (infobox with title, description, attributes, profiles)
- **FAQ** (frequently asked questions with sourced answers from Brave)
- **Reddit Threads** with verified engagement (upvotes, upvote_ratio, comments, top comment insights)
- **X Posts** with full engagement (likes, reposts, replies, quotes, views, bookmarks, has_media flag)
- **HackerNews** with verified points and comments
- **News Articles** from news sources with publication dates
- **Web Results** with schema-enriched data (ratings, reviews, products, articles, books, recipes, Q&A) and deep results (sitelinks, nested news)
- **Videos** from YouTube and other platforms (with creator, duration)
- **Forum Discussions** from Stack Overflow, Discourse, etc. (with engagement proxy from snippet richness)

**Depth options** (passed through from user's command):
- `--quick` -> Faster, fewer sources
- (default) -> Balanced
- `--deep` -> Comprehensive research with more pages

---

## Judge Agent: Synthesize All Sources

**After the script completes, internally synthesize (don't display stats yet):**

The Judge Agent must:
1. Weight Reddit/X/HN sources HIGHER (they have verified engagement signals: upvotes, likes, points)
2. Weight News/Web/Video sources based on recency and relevance scores
3. Use the AI Summary as a starting point if available
4. Identify patterns that appear across MULTIPLE sources (strongest signals)
5. Note any contradictions between sources
6. Extract the top 3-5 actionable insights

**Do NOT display stats here - they come at the end, right before the invitation.**

---

## FIRST: Internalize the Research

**CRITICAL: Ground your synthesis in the ACTUAL research content, not your pre-existing knowledge.**

Read the research output carefully. Pay attention to:
- **Exact product/tool names** mentioned (e.g., if research mentions "ClawdBot" or "@clawdbot", that's a DIFFERENT product than "Claude Code" - don't conflate them)
- **Specific quotes and insights** from the sources - use THESE, not generic knowledge
- **What the sources actually say**, not what you assume the topic is about
- **AI Summary** - if available, use it as a synthesis starting point but verify against individual sources

**ANTI-PATTERN TO AVOID**: If user asks about "clawdbot skills" and research returns ClawdBot content (self-hosted AI agent), do NOT synthesize this as "Claude Code skills" just because both involve "skills". Read what the research actually says.

### If QUERY_TYPE = RECOMMENDATIONS

**CRITICAL: Extract SPECIFIC NAMES, not generic patterns.**

When user asks "best X" or "top X", they want a LIST of specific things:
- Scan research for specific product names, tool names, project names, skill names, etc.
- Count how many times each is mentioned
- Note which sources recommend each (Reddit thread, X post, news article, blog)
- List them by popularity/mention count

**BAD synthesis for "best Claude Code skills":**
> "Skills are powerful. Keep them under 500 lines. Use progressive disclosure."

**GOOD synthesis for "best Claude Code skills":**
> "Most mentioned skills: /commit (5 mentions), remotion skill (4x), git-worktree (3x), /pr (3x). The Remotion announcement got 16K likes on X."

### For all QUERY_TYPEs

Identify from the ACTUAL RESEARCH OUTPUT:
- **PROMPT FORMAT** - Does research recommend JSON, structured params, natural language, keywords? THIS IS CRITICAL.
- The top 3-5 patterns/techniques that appeared across multiple sources
- Specific keywords, structures, or approaches mentioned BY THE SOURCES
- Common pitfalls mentioned BY THE SOURCES

**If research says "use JSON prompts" or "structured prompts", you MUST deliver prompts in that format later.**

---

## THEN: Show Summary + Invite Vision

**CRITICAL: Do NOT output any "Sources:" lists. The final display should be clean.**

**Display in this EXACT sequence:**

**FIRST - What I learned (based on QUERY_TYPE):**

**If RECOMMENDATIONS** - Show specific things mentioned:
```
Most mentioned:
1. [Specific name] - mentioned {n}x (r/sub, @handle, news.com)
2. [Specific name] - mentioned {n}x (sources)
3. [Specific name] - mentioned {n}x (sources)
4. [Specific name] - mentioned {n}x (sources)
5. [Specific name] - mentioned {n}x (sources)

Notable mentions: [other specific things with 1-2 mentions]
```

**If PROMPTING/NEWS/GENERAL** - Show synthesis and patterns:
```
What I learned:

[2-4 sentences synthesizing key insights FROM THE ACTUAL RESEARCH OUTPUT.]

KEY PATTERNS I'll use:
1. [Pattern from research]
2. [Pattern from research]
3. [Pattern from research]
```

**THEN - Stats (right before invitation):**

For **full mode** (both BRAVE + XAI keys):
```
---
All agents reported back!
Data Quality: {n} items | {n}% verified dates | {n}% verified engagement | avg {n} days old
|- Reddit: {n} threads | {sum} upvotes | {sum} comments (engagement verified)
|- X: {n} posts | {sum} likes | {sum} reposts | {sum} views
|- HN: {n} stories | {sum} points (engagement verified)
|- News: {n} articles
|- Web: {n} pages ({n} with schema data, {n} with deep results)
|- Videos: {n} videos
|- Discussions: {n} forums
|- AI Summary: Available | Knowledge Panel: Available | FAQ: {n} entries
|- Top voices: r/{sub1}, r/{sub2} | @{handle1}, @{handle2}
```

For **brave mode** (BRAVE_API_KEY only):
```
---
Research complete!
Data Quality: {n} items | {n}% verified dates | avg {n} days old
|- Reddit: {n} threads | {sum} upvotes | {sum} comments
|- HN: {n} stories | {sum} points
|- News: {n} articles
|- Web: {n} pages | Videos: {n} | Discussions: {n}

Tip: Add XAI_API_KEY to ~/.config/last30days/.env for X/Twitter data
```

For **HN-only mode** (no API keys):
```
---
Research complete!
|- HN: {n} stories | {sum} points

Want better results? Add API keys to ~/.config/last30days/.env
- BRAVE_API_KEY -> Reddit, News, Web, Videos, Discussions
- XAI_API_KEY -> X/Twitter (real likes & reposts)
```

**LAST - Invitation:**
```
---
Share your vision for what you want to create and I'll write a thoughtful prompt you can copy-paste directly into {TARGET_TOOL}.
```

**Use real numbers from the research output.** The patterns should be actual insights from the research, not generic advice.

**SELF-CHECK before displaying**: Re-read your "What I learned" section. Does it match what the research ACTUALLY says? If the research was about ClawdBot (a self-hosted AI agent), your summary should be about ClawdBot, not Claude Code. If you catch yourself projecting your own knowledge instead of the research, rewrite it.

**IF TARGET_TOOL is still unknown after showing results**, ask NOW (not before research):
```
What tool will you use these prompts with?

Options:
1. [Most relevant tool based on research - e.g., if research mentioned Figma/Sketch, offer those]
2. Nano Banana Pro (image generation)
3. ChatGPT / Claude (text/code)
4. Other (tell me)
```

**IMPORTANT**: After displaying this, WAIT for the user to respond. Don't dump generic prompts.

---

## WAIT FOR USER'S VISION

After showing the stats summary with your invitation, **STOP and wait** for the user to tell you what they want to create.

When they respond with their vision (e.g., "I want a landing page mockup for my SaaS app"), THEN write a single, thoughtful, tailored prompt.

---

## WHEN USER SHARES THEIR VISION: Write ONE Perfect Prompt

Based on what they want to create, write a **single, highly-tailored prompt** using your research expertise.

### CRITICAL: Match the FORMAT the research recommends

**If research says to use a specific prompt FORMAT, YOU MUST USE THAT FORMAT:**

- Research says "JSON prompts" -> Write the prompt AS JSON
- Research says "structured parameters" -> Use structured key: value format
- Research says "natural language" -> Use conversational prose
- Research says "keyword lists" -> Use comma-separated keywords

**ANTI-PATTERN**: Research says "use JSON prompts with device specs" but you write plain prose. This defeats the entire purpose of the research.

### Output Format:

```
Here's your prompt for {TARGET_TOOL}:

---

[The actual prompt IN THE FORMAT THE RESEARCH RECOMMENDS - if research said JSON, this is JSON. If research said natural language, this is prose. Match what works.]

---

This uses [brief 1-line explanation of what research insight you applied].
```

### Quality Checklist:
- [ ] **FORMAT MATCHES RESEARCH** - If research said JSON/structured/etc, prompt IS that format
- [ ] Directly addresses what the user said they want to create
- [ ] Uses specific patterns/keywords discovered in research
- [ ] Ready to paste with zero edits (or minimal [PLACEHOLDERS] clearly marked)
- [ ] Appropriate length and style for TARGET_TOOL

---

## IF USER ASKS FOR MORE OPTIONS

Only if they ask for alternatives or more prompts, provide 2-3 variations. Don't dump a prompt pack unless requested.

---

## AFTER EACH PROMPT: Stay in Expert Mode

After delivering a prompt, offer to write more:

> Want another prompt? Just tell me what you're creating next.

---

## CONTEXT MEMORY

For the rest of this conversation, remember:
- **TOPIC**: {topic}
- **TARGET_TOOL**: {tool}
- **KEY PATTERNS**: {list the top 3-5 patterns you learned}
- **RESEARCH FINDINGS**: The key facts and insights from the research

**CRITICAL: After research is complete, you are now an EXPERT on this topic.**

When the user asks follow-up questions:
- **DO NOT run new searches** - you already have the research
- **Answer from what you learned** - cite the Reddit threads, X posts, news articles, and web sources
- **If they ask for a prompt** - write one using your expertise
- **If they ask a question** - answer it from your research findings

Only do new research if the user explicitly asks about a DIFFERENT topic.

---

## Output Summary Footer (After Each Prompt)

After delivering a prompt, end with:

For **full mode**:
```
---
Expert in: {TOPIC} for {TARGET_TOOL}
Based on: {n} Reddit threads ({sum} upvotes) + {n} X posts ({sum} likes, {sum} views) + {n} HN stories + {n} news + {n} web pages + {n} videos + {n} discussions

Want another prompt? Just tell me what you're creating next.
```

For **HN-only mode**:
```
---
Expert in: {TOPIC} for {TARGET_TOOL}
Based on: {n} HN stories ({sum} points)

Want another prompt? Just tell me what you're creating next.

Unlock more sources: Add API keys to ~/.config/last30days/.env
```
