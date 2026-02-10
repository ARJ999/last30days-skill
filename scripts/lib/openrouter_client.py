"""OpenRouter API client for Perplexity Sonar models (stdlib only)."""

import sys
import time
from typing import Any, Dict, List, Optional

from . import http


# OpenRouter API endpoint
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Perplexity model IDs on OpenRouter
SONAR_PRO_SEARCH = "perplexity/sonar-pro-search"
SONAR_DEEP_RESEARCH = "perplexity/sonar-deep-research"

# Rate limit retry config
MAX_RATE_LIMIT_RETRIES = 4
RATE_LIMIT_BACKOFF_BASE = 1.0  # seconds


def _log(msg: str):
    """Log to stderr."""
    sys.stderr.write(f"[OPENROUTER] {msg}\n")
    sys.stderr.flush()


class OpenRouterError(Exception):
    """OpenRouter API error with status code."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OpenRouterClient:
    """OpenRouter API client for Perplexity Sonar models.

    Handles authentication, rate limiting, and Perplexity-specific parameter
    passthrough for sonar-pro-search and sonar-deep-research.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/last30days-skill",
            "X-Title": "last30days",
        }

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.3,
        search_domain_filter: Optional[List[str]] = None,
        search_recency_filter: Optional[str] = None,
        search_after_date_filter: Optional[str] = None,
        search_before_date_filter: Optional[str] = None,
        return_related_questions: bool = False,
        search_context_size: Optional[str] = None,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Send chat completion request through OpenRouter.

        Args:
            model: Model ID (e.g. perplexity/sonar-pro-search)
            messages: Chat messages
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            search_domain_filter: Include/exclude domains (prefix with - to exclude)
            search_recency_filter: "hour", "day", "week", "month"
            search_after_date_filter: Date in MM/DD/YYYY format
            search_before_date_filter: Date in MM/DD/YYYY format
            return_related_questions: Return follow-up questions
            search_context_size: "low", "medium", "high" (not for deep-research)
            timeout: Request timeout in seconds

        Returns:
            Full API response dict

        Raises:
            OpenRouterError: On API errors
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        # Perplexity-specific params (passed through by OpenRouter)
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter
        if search_after_date_filter:
            payload["search_after_date_filter"] = search_after_date_filter
        if search_before_date_filter:
            payload["search_before_date_filter"] = search_before_date_filter
        if return_related_questions:
            payload["return_related_questions"] = True
        if search_context_size and model != SONAR_DEEP_RESEARCH:
            payload["web_search_options"] = {"search_context_size": search_context_size}

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return http.post(
                    OPENROUTER_CHAT_URL, payload,
                    headers=self._headers, timeout=timeout,
                )
            except http.HTTPError as e:
                if e.status_code == 429:
                    if attempt < MAX_RATE_LIMIT_RETRIES:
                        wait = RATE_LIMIT_BACKOFF_BASE * (2 ** attempt)
                        _log(f"Rate limited (429), retrying in {wait:.0f}s (attempt {attempt + 1}/{MAX_RATE_LIMIT_RETRIES})")
                        time.sleep(wait)
                        continue
                    raise OpenRouterError("Rate limit exceeded after retries", 429)
                elif e.status_code == 401:
                    raise OpenRouterError(
                        "Invalid OPENROUTER_API_KEY. Check your key at openrouter.ai/settings/keys",
                        401,
                    )
                elif e.status_code == 402:
                    raise OpenRouterError(
                        "OpenRouter credits exhausted. Add credits at openrouter.ai/credits",
                        402,
                    )
                else:
                    raise OpenRouterError(
                        f"OpenRouter API error {e.status_code}: {e}",
                        e.status_code,
                    )

        raise OpenRouterError("Request failed after retries")


def extract_content(response: Dict[str, Any]) -> str:
    """Extract message content from OpenRouter response."""
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "")


def extract_citations(response: Dict[str, Any]) -> List[str]:
    """Extract citation URLs from top-level citations array."""
    return response.get("citations", [])


def extract_annotations(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract rich annotations (url_citation) from response message."""
    choices = response.get("choices", [])
    if not choices:
        return []
    message = choices[0].get("message", {})
    annotations = message.get("annotations", [])
    result = []
    for ann in annotations:
        if not isinstance(ann, dict):
            continue
        if ann.get("type") == "url_citation":
            cite = ann.get("url_citation", {})
            if cite.get("url"):
                result.append({
                    "url": cite["url"],
                    "title": cite.get("title", ""),
                    "snippet": cite.get("content", ""),
                })
    return result


def format_date_filter(date_str: str) -> str:
    """Convert YYYY-MM-DD to MM/DD/YYYY for Perplexity date filter."""
    parts = date_str.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    return date_str
