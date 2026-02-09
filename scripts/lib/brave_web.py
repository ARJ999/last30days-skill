"""Brave Web Search for general web results, discussions, FAQ, infobox, and summarizer key."""

import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import brave_client, dates

# Default Goggles for general web search (inline DSL)
DEFAULT_GOGGLES = "$discard,site=pinterest.com\n$boost=2,site=github.com\n$boost=2,site=dev.to\n$boost=2,site=stackoverflow.com"

# Depth config: (pages_to_fetch,)
DEPTH_PAGES = {
    "quick": 1,
    "default": 2,
    "deep": 3,
}


def _log(msg: str):
    sys.stderr.write(f"[BRAVE-WEB] {msg}\n")
    sys.stderr.flush()


def _parse_page_age(page_age: Optional[str]) -> Optional[str]:
    """Parse Brave's page_age field to YYYY-MM-DD."""
    if not page_age:
        return None
    # page_age is ISO 8601 datetime string
    parsed = dates.parse_date(page_age)
    if parsed:
        return parsed.date().isoformat()
    # Try extracting just the date portion
    match = re.match(r'(\d{4}-\d{2}-\d{2})', str(page_age))
    if match:
        return match.group(1)
    return None


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def _extract_rating(raw: Any) -> Optional[Dict[str, Any]]:
    """Extract rating from a Brave result field."""
    if not isinstance(raw, dict):
        return None
    rating = {}
    if "ratingValue" in raw or "best_rating" in raw or "review_count" in raw:
        if raw.get("ratingValue") is not None:
            rating["value"] = raw["ratingValue"]
        if raw.get("best_rating") is not None:
            rating["best"] = raw["best_rating"]
        if raw.get("review_count") is not None:
            rating["review_count"] = raw["review_count"]
        return rating if rating else None
    return None


def _extract_schema_data(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract schema.org structured data from a web search result.

    Brave Pro AI returns rich structured data including ratings, reviews,
    articles, products, recipes, books, creative works, and more.
    """
    data = {}

    # Rating (standalone or embedded in other schemas)
    rating_raw = result.get("rating")
    if isinstance(rating_raw, dict):
        rating = _extract_rating(rating_raw)
        if rating:
            data["rating"] = rating

    # Article metadata
    article = result.get("article")
    if isinstance(article, dict):
        art = {}
        authors = article.get("author", [])
        if authors and isinstance(authors, list):
            art["authors"] = [a.get("name", "") for a in authors if isinstance(a, dict) and a.get("name")]
        if article.get("date"):
            art["date"] = article["date"]
        publisher = article.get("publisher")
        if isinstance(publisher, dict) and publisher.get("name"):
            art["publisher"] = publisher["name"]
        if article.get("isAccessibleForFree") is not None:
            art["is_free"] = article["isAccessibleForFree"]
        if art:
            data["article"] = art

    # Review
    review = result.get("review")
    if isinstance(review, dict):
        rev = {}
        if review.get("name"):
            rev["name"] = review["name"][:100]
        if review.get("description"):
            rev["description"] = review["description"][:200]
        rev_rating = review.get("rating")
        if isinstance(rev_rating, dict):
            parsed = _extract_rating(rev_rating)
            if parsed:
                rev["rating"] = parsed
        if rev:
            data["review"] = rev

    # Product cluster
    product = result.get("product_cluster") or result.get("product")
    if isinstance(product, list) and product:
        product = product[0]
    if isinstance(product, dict):
        prod = {}
        if product.get("name"):
            prod["name"] = product["name"][:100]
        prod_rating = product.get("rating")
        if isinstance(prod_rating, dict):
            parsed = _extract_rating(prod_rating)
            if parsed:
                prod["rating"] = parsed
        if prod:
            data["product"] = prod

    # Recipe
    recipe = result.get("recipe")
    if isinstance(recipe, dict):
        rec = {}
        if recipe.get("name"):
            rec["name"] = recipe["name"][:100]
        rec_rating = recipe.get("rating")
        if isinstance(rec_rating, dict):
            parsed = _extract_rating(rec_rating)
            if parsed:
                rec["rating"] = parsed
        if rec:
            data["recipe"] = rec

    # Book
    book = result.get("book")
    if isinstance(book, dict):
        bk = {}
        if book.get("title"):
            bk["title"] = book["title"][:100]
        authors = book.get("author", [])
        if authors and isinstance(authors, list):
            bk["authors"] = [a.get("name", "") for a in authors if isinstance(a, dict) and a.get("name")]
        if book.get("date"):
            bk["date"] = book["date"]
        if book.get("pages"):
            bk["pages"] = book["pages"]
        bk_rating = book.get("rating")
        if isinstance(bk_rating, dict):
            parsed = _extract_rating(bk_rating)
            if parsed:
                bk["rating"] = parsed
        if bk:
            data["book"] = bk

    # Creative work (music, film, etc.)
    creative = result.get("creative_work")
    if isinstance(creative, dict):
        cw = {}
        if creative.get("name"):
            cw["name"] = creative["name"][:100]
        cw_rating = creative.get("rating")
        if isinstance(cw_rating, dict):
            parsed = _extract_rating(cw_rating)
            if parsed:
                cw["rating"] = parsed
        if cw:
            data["creative_work"] = cw

    # Movie
    movie = result.get("movie")
    if isinstance(movie, dict):
        mv = {}
        if movie.get("name"):
            mv["name"] = movie["name"][:100]
        mv_rating = movie.get("rating")
        if isinstance(mv_rating, dict):
            parsed = _extract_rating(mv_rating)
            if parsed:
                mv["rating"] = parsed
        if mv:
            data["movie"] = mv

    # Q&A
    qa = result.get("qa")
    if isinstance(qa, dict):
        q = {}
        if qa.get("question"):
            q["question"] = qa["question"][:200]
        if qa.get("answer"):
            q["answer"] = qa["answer"][:300]
        if q:
            data["qa"] = q

    # Music recording
    music = result.get("music_recording")
    if isinstance(music, dict):
        mr = {}
        if music.get("name"):
            mr["name"] = music["name"][:100]
        mr_rating = music.get("rating")
        if isinstance(mr_rating, dict):
            parsed = _extract_rating(mr_rating)
            if parsed:
                mr["rating"] = parsed
        if mr:
            data["music"] = mr

    # Result subtype (e.g. "generic", "article", "product")
    subtype = result.get("subtype")
    if subtype:
        data["subtype"] = subtype

    return data if data else None


def _extract_deep_results(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract deep results (aggregated nested content) from a web search result.

    Deep results contain news articles, sitelink buttons, social profiles,
    videos, and images found within the context of this web result.
    """
    deep = result.get("deep_results")
    if not isinstance(deep, dict):
        return None

    data = {}

    # Sitelink buttons (sub-pages of the domain)
    buttons = deep.get("buttons", [])
    if isinstance(buttons, list) and buttons:
        data["buttons"] = [
            {"title": b.get("title", "")[:80], "url": b.get("url", "")}
            for b in buttons[:6]
            if isinstance(b, dict) and b.get("title")
        ]

    # Nested news results
    news = deep.get("news", [])
    if isinstance(news, list) and news:
        data["news"] = [
            {"title": n.get("title", "")[:120], "url": n.get("url", ""), "age": n.get("age", "")}
            for n in news[:3]
            if isinstance(n, dict) and n.get("title")
        ]

    # Social profiles
    social = deep.get("social", [])
    if isinstance(social, list) and social:
        data["social"] = [
            {"name": s.get("long_name", s.get("name", ""))[:60], "url": s.get("url", "")}
            for s in social[:5]
            if isinstance(s, dict) and (s.get("name") or s.get("long_name"))
        ]

    # Nested videos
    videos = deep.get("videos", [])
    if isinstance(videos, list) and videos:
        data["videos"] = [
            {"title": v.get("title", "")[:120], "url": v.get("url", "")}
            for v in videos[:3]
            if isinstance(v, dict) and v.get("title")
        ]

    return data if data else None


def search_web(
    client: brave_client.BraveClient,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> Dict[str, Any]:
    """Search Brave Web with discussions, FAQ, infobox, and summarizer key.

    Single API call returns multiple result types. Handles pagination for deeper research.

    Returns:
        Merged Brave Web Search response (all pages combined)
    """
    freshness = f"{from_date}to{to_date}"
    pages = DEPTH_PAGES.get(depth, 2)

    # First page includes all extras
    all_web_results = []
    discussions_results = []
    faq_data = None
    infobox_data = None
    summarizer_key = None
    query_info = None

    for page in range(pages):
        try:
            response = client.web_search(
                q=topic,
                freshness=freshness,
                count=20,
                offset=page,
                extra_snippets=True,
                summary=(page == 0),  # Only request summarizer on first page
                result_filter="discussions,faq,infobox" if page == 0 else None,
                goggles=DEFAULT_GOGGLES,
            )
        except brave_client.BraveError as e:
            _log(f"Page {page} error: {e}")
            if page == 0:
                raise  # First page failure is fatal
            break

        # Extract web results
        web = response.get("web", {})
        all_web_results.extend(web.get("results", []))

        # First page extras
        if page == 0:
            query_info = response.get("query", {})
            discussions_resp = response.get("discussions", {})
            if discussions_resp:
                discussions_results = discussions_resp.get("results", [])
            faq_resp = response.get("faq", {})
            if faq_resp:
                faq_data = faq_resp
            infobox_resp = response.get("infobox", {})
            if infobox_resp:
                infobox_data = infobox_resp
            summ_resp = response.get("summarizer", {})
            if summ_resp and summ_resp.get("key"):
                summarizer_key = summ_resp["key"]

        # Check if more results available
        q = response.get("query", {})
        if not q.get("more_results_available", False):
            break

    return {
        "web_results": all_web_results,
        "discussions": discussions_results,
        "faq": faq_data,
        "infobox": infobox_data,
        "summarizer_key": summarizer_key,
        "query": query_info,
    }


def parse_web_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse web results from Brave response into item dicts."""
    items = []
    results = response.get("web_results", [])

    total = len(results)
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            continue

        url = result.get("url", "")
        if not url:
            continue

        domain = _extract_domain(url)

        # Skip social media domains (covered by dedicated sources)
        if any(d in domain for d in ["reddit.com", "twitter.com", "x.com", "news.ycombinator.com"]):
            continue

        title = result.get("title", "").strip()
        description = result.get("description", "").strip()
        extra_snippets = result.get("extra_snippets", [])
        page_age = _parse_page_age(result.get("page_age"))
        has_schema = bool(result.get("schemas"))

        # Extract schema.org structured data
        schema_data = _extract_schema_data(result)

        # Extract deep results (nested news, buttons, videos, images)
        deep_results = _extract_deep_results(result)

        # Position-based relevance
        relevance = max(0.2, 1.0 - (i / max(total, 1)) * 0.8)

        items.append({
            "id": f"W{len(items)+1}",
            "title": title[:200],
            "url": url,
            "source_domain": domain,
            "snippet": description[:300],
            "extra_snippets": [s[:200] for s in (extra_snippets or [])[:5]],
            "date": page_age,
            "has_schema_data": has_schema,
            "schema_data": schema_data,
            "deep_results": deep_results,
            "relevance": relevance,
            "why_relevant": description[:150] if description else title[:150],
        })

    return items


def parse_discussions(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse discussion results (non-Reddit forums) from Brave response."""
    items = []
    results = response.get("discussions", [])

    total = len(results)
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            continue

        url = result.get("url", "")
        if not url:
            continue

        domain = _extract_domain(url)

        # Skip Reddit discussions (covered by brave_reddit.py)
        if "reddit.com" in domain:
            continue

        title = result.get("title", "").strip()
        description = result.get("description", "").strip()
        extra_snippets = result.get("extra_snippets", [])
        page_age = _parse_page_age(result.get("page_age"))

        # Determine forum name from domain
        forum_map = {
            "stackoverflow.com": "Stack Overflow",
            "stackexchange.com": "Stack Exchange",
            "news.ycombinator.com": "HackerNews",
            "discourse.org": "Discourse",
        }
        forum_name = forum_map.get(domain, domain)

        # Position-based relevance
        relevance = max(0.2, 1.0 - (i / max(total, 1)) * 0.8)

        items.append({
            "id": f"D{len(items)+1}",
            "title": title[:200],
            "url": url,
            "forum_name": forum_name,
            "snippet": description[:300],
            "extra_snippets": [s[:200] for s in (extra_snippets or [])[:5]],
            "date": page_age,
            "relevance": relevance,
            "why_relevant": description[:150] if description else title[:150],
        })

    return items


def parse_faq(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse FAQ results from Brave response."""
    faq_data = response.get("faq")
    if not faq_data:
        return []

    faqs = []
    results = faq_data.get("results", [])
    for result in results:
        if not isinstance(result, dict):
            continue
        question = result.get("question", "").strip()
        answer = result.get("answer", "").strip()
        url = result.get("url", "")
        if question and answer:
            faqs.append({
                "question": question,
                "answer": answer[:500],
                "url": url,
            })

    return faqs


def parse_infobox(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse infobox (knowledge panel) from Brave response."""
    infobox = response.get("infobox")
    if not infobox:
        return None

    # Extract key infobox fields
    result = {}
    if isinstance(infobox, dict):
        # Could be a single infobox or nested in results
        if "results" in infobox:
            results = infobox["results"]
            if results and isinstance(results, list):
                infobox = results[0]

        result = {
            "title": infobox.get("title", ""),
            "description": infobox.get("description", ""),
            "long_description": infobox.get("long_desc", ""),
            "url": infobox.get("url", ""),
            "attributes": infobox.get("attributes", []),
            "type": infobox.get("subtype", infobox.get("type", "")),
        }

        # Extract thumbnail
        thumbnail = infobox.get("thumbnail")
        if isinstance(thumbnail, dict):
            result["thumbnail_url"] = thumbnail.get("src", "")

        # Extract profiles
        profiles = infobox.get("profiles", [])
        if profiles:
            result["profiles"] = [
                {"name": p.get("long_name", p.get("name", "")), "url": p.get("url", "")}
                for p in profiles[:5]
            ]

    return result if result.get("title") else None


def get_summarizer_key(response: Dict[str, Any]) -> Optional[str]:
    """Extract summarizer key from Brave web search response."""
    return response.get("summarizer_key")
