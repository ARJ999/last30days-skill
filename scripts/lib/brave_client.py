"""Brave Search API client for last30days skill (stdlib only)."""

import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from . import http


# Brave Search API endpoints
BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_NEWS_SEARCH_URL = "https://api.search.brave.com/res/v1/news/search"
BRAVE_VIDEO_SEARCH_URL = "https://api.search.brave.com/res/v1/videos/search"
BRAVE_SUMMARIZER_URL = "https://api.search.brave.com/res/v1/summarizer/search"

# Rate limit retry config
MAX_RATE_LIMIT_RETRIES = 4
RATE_LIMIT_BACKOFF_BASE = 1.0  # seconds


def _log(msg: str):
    """Log to stderr."""
    sys.stderr.write(f"[BRAVE] {msg}\n")
    sys.stderr.flush()


class BraveError(Exception):
    """Brave API error with status code and error code."""
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class BraveClient:
    """Brave Search API client.

    Handles authentication, rate limiting, and error mapping for all Brave endpoints.
    Reuses the stdlib-only HTTP client from http.py.
    """

    def __init__(self, api_key: str, search_lang: str = None, country: str = None):
        self.api_key = api_key
        self.search_lang = search_lang
        self.country = country
        self._headers = {
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

    def _request(self, url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Make authenticated GET request to Brave API with rate limit handling.

        Args:
            url: Base endpoint URL
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            BraveError: On API errors
        """
        # Build query string, filtering out None values
        filtered_params = {k: v for k, v in params.items() if v is not None}
        full_url = f"{url}?{urlencode(filtered_params)}"

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return http.get(full_url, headers=self._headers, timeout=timeout, retries=1)
            except http.HTTPError as e:
                if e.status_code == 429:
                    if attempt < MAX_RATE_LIMIT_RETRIES:
                        wait = RATE_LIMIT_BACKOFF_BASE * (2 ** attempt)
                        _log(f"Rate limited (429), retrying in {wait:.0f}s (attempt {attempt + 1}/{MAX_RATE_LIMIT_RETRIES})")
                        time.sleep(wait)
                        continue
                    raise BraveError("Rate limit exceeded after retries", 429, "RATE_LIMIT_EXCEEDED")
                elif e.status_code == 401:
                    raise BraveError(
                        "Invalid BRAVE_API_KEY. Check your key at api-dashboard.search.brave.com",
                        401, "SUBSCRIPTION_TOKEN_INVALID",
                    )
                elif e.status_code == 403:
                    raise BraveError(
                        "Brave plan does not include this feature. Pro Data AI plan required.",
                        403, "PLAN_INSUFFICIENT",
                    )
                elif e.status_code == 422:
                    raise BraveError(
                        f"Invalid request parameters: {e.body or 'unknown'}",
                        422, "INVALID_PARAMS",
                    )
                else:
                    raise BraveError(
                        f"Brave API error {e.status_code}: {e}",
                        e.status_code,
                    )

        raise BraveError("Request failed after retries")

    def web_search(
        self,
        q: str,
        freshness: Optional[str] = None,
        count: int = 20,
        offset: int = 0,
        extra_snippets: bool = True,
        summary: bool = False,
        result_filter: Optional[str] = None,
        goggles: Optional[str] = None,
        search_lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Brave Web Search.

        Args:
            q: Search query (max 400 chars, 50 words)
            freshness: Date filter - 'pd', 'pw', 'pm', 'py', or 'YYYY-MM-DDtoYYYY-MM-DD'
            count: Results per page (max 20)
            offset: Page offset (0-9)
            extra_snippets: Return up to 5 additional excerpts per result
            summary: Request summarizer key in response
            result_filter: Comma-separated result types (web,discussions,faq,infobox,etc.)
            goggles: Custom re-ranking rules (inline DSL or URL)
            search_lang: Language for search results (e.g. 'en')
            country: Country for search localization (e.g. 'us')

        Returns:
            Full Brave Web Search response
        """
        params = {
            "q": q[:400],
            "count": min(count, 20),
            "offset": min(offset, 9),
            "safesearch": "off",
            "extra_snippets": str(extra_snippets).lower(),
            "text_decorations": "false",
            "spellcheck": "true",
        }
        if freshness:
            params["freshness"] = freshness
        if summary:
            params["summary"] = "1"
        if result_filter:
            params["result_filter"] = result_filter
        if goggles:
            params["goggles"] = goggles
        lang = search_lang or self.search_lang
        ctry = country or self.country
        if lang:
            params["search_lang"] = lang
        if ctry:
            params["country"] = ctry

        return self._request(BRAVE_WEB_SEARCH_URL, params)

    def news_search(
        self,
        q: str,
        freshness: Optional[str] = None,
        count: int = 20,
        offset: int = 0,
        extra_snippets: bool = True,
        search_lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Brave News Search.

        Args:
            q: Search query
            freshness: Date filter
            count: Results per page (max 50 for news)
            offset: Page offset (0-9)
            extra_snippets: Return additional excerpts
            search_lang: Language for search results
            country: Country for localization

        Returns:
            Brave News Search response
        """
        params = {
            "q": q[:400],
            "count": min(count, 50),
            "offset": min(offset, 9),
            "safesearch": "off",
            "extra_snippets": str(extra_snippets).lower(),
            "spellcheck": "true",
        }
        if freshness:
            params["freshness"] = freshness
        lang = search_lang or self.search_lang
        ctry = country or self.country
        if lang:
            params["search_lang"] = lang
        if ctry:
            params["country"] = ctry

        return self._request(BRAVE_NEWS_SEARCH_URL, params)

    def video_search(
        self,
        q: str,
        freshness: Optional[str] = None,
        count: int = 20,
        offset: int = 0,
        search_lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Brave Video Search.

        Args:
            q: Search query
            freshness: Date filter
            count: Results per page
            offset: Page offset
            search_lang: Language for search results
            country: Country for localization

        Returns:
            Brave Video Search response
        """
        params = {
            "q": q[:400],
            "count": min(count, 20),
            "offset": min(offset, 9),
            "safesearch": "off",
            "spellcheck": "true",
        }
        if freshness:
            params["freshness"] = freshness
        lang = search_lang or self.search_lang
        ctry = country or self.country
        if lang:
            params["search_lang"] = lang
        if ctry:
            params["country"] = ctry

        return self._request(BRAVE_VIDEO_SEARCH_URL, params)

    def summarizer_search(
        self,
        key: str,
        inline_references: bool = True,
    ) -> Dict[str, Any]:
        """Fetch AI summary using summarizer key from web search.

        This is step 2 of the two-step summarizer flow. The key comes from
        a web search response that included summary=1.

        Not billed separately - only the original web search counts.

        Args:
            key: Opaque summarizer key from web search response
            inline_references: Include [n]-style citation markers in summary

        Returns:
            Summarizer response with summary text and citations
        """
        params = {
            "key": key,
            "inline_references": str(inline_references).lower(),
            "entity_info": "1",
        }

        return self._request(BRAVE_SUMMARIZER_URL, params)
