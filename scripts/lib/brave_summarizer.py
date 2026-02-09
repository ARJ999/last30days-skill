"""Brave Summarizer for AI summary with citations (two-step flow)."""

import sys
from typing import Any, Dict, List, Optional

from . import brave_client


def _log(msg: str):
    sys.stderr.write(f"[BRAVE-SUMMARIZER] {msg}\n")
    sys.stderr.flush()


def fetch_summary(
    client: brave_client.BraveClient,
    summarizer_key: str,
) -> Optional[Dict[str, Any]]:
    """Fetch AI summary using summarizer key from web search.

    Step 2 of the two-step summarizer flow.
    Not billed separately - only the original web search counts.

    Args:
        client: BraveClient instance
        summarizer_key: Opaque key from web search response

    Returns:
        Dict with 'summary', 'citations', 'followups' or None on failure
    """
    if not summarizer_key:
        return None

    try:
        response = client.summarizer_search(
            key=summarizer_key,
            inline_references=True,
        )
        return response
    except brave_client.BraveError as e:
        _log(f"Summarizer error: {e}")
        return None
    except Exception as e:
        _log(f"Unexpected summarizer error: {e}")
        return None


def parse_summary_response(response: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse Brave summarizer response.

    Returns:
        Dict with:
            summary: str - Summary text (may include [n] citation markers)
            citations: List[Dict] - Citation references
            followups: List[str] - Suggested follow-up questions
    """
    result = {
        "summary": None,
        "citations": [],
        "followups": [],
    }

    if not response:
        return result

    # Extract summary text
    # The summarizer response structure can vary
    if isinstance(response, dict):
        # Try direct summary field
        if "summary" in response:
            summary_data = response["summary"]
            if isinstance(summary_data, str):
                result["summary"] = summary_data
            elif isinstance(summary_data, list):
                # Sometimes returned as list of text segments
                result["summary"] = " ".join(
                    s.get("text", str(s)) if isinstance(s, dict) else str(s)
                    for s in summary_data
                )
            elif isinstance(summary_data, dict):
                result["summary"] = summary_data.get("text", "")

        # Try 'results' wrapper
        if not result["summary"] and "results" in response:
            results = response["results"]
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    result["summary"] = first.get("text", first.get("summary", ""))

        # Try 'message' or 'text' direct fields
        if not result["summary"]:
            result["summary"] = response.get("text", response.get("message", None))

        # Extract citations (references)
        enrichments = response.get("enrichments", {})
        if isinstance(enrichments, dict):
            refs = enrichments.get("references", [])
            if isinstance(refs, list):
                result["citations"] = [
                    {"number": r.get("number", i+1), "url": r.get("url", ""), "title": r.get("title", "")}
                    for i, r in enumerate(refs)
                    if isinstance(r, dict)
                ]

        # Also check top-level references
        if not result["citations"]:
            refs = response.get("references", [])
            if isinstance(refs, list):
                result["citations"] = [
                    {"number": r.get("number", i+1), "url": r.get("url", ""), "title": r.get("title", "")}
                    for i, r in enumerate(refs)
                    if isinstance(r, dict)
                ]

        # Extract follow-up questions
        followups = response.get("followups", [])
        if isinstance(followups, list):
            result["followups"] = [
                f.get("text", str(f)) if isinstance(f, dict) else str(f)
                for f in followups
                if f
            ]

        # Also check 'enrichments.followups'
        if not result["followups"] and isinstance(enrichments, dict):
            followups = enrichments.get("followups", [])
            if isinstance(followups, list):
                result["followups"] = [
                    f.get("text", str(f)) if isinstance(f, dict) else str(f)
                    for f in followups
                    if f
                ]

    return result
