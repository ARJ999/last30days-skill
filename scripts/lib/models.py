"""Model selection for last30days skill (xAI only).

Brave Search API requires no model selection - it is a direct search API.
Only xAI (for X/Twitter search via grok models) needs model selection.
"""

import sys
from typing import Any, Dict, List, Optional

from . import cache, http


def _log(msg: str):
    """Log to stderr."""
    sys.stderr.write(f"[MODELS] {msg}\n")
    sys.stderr.flush()


# xAI model configuration
XAI_MODELS_URL = "https://api.x.ai/v1/models"

# Preferred models in order (latest first)
# grok-4-1-fast-reasoning: best quality for agentic search with chain-of-thought
# grok-4-1-fast: fast agentic tool calling (x_search, web_search)
XAI_PREFERRED_MODELS = [
    "grok-4-1-fast-reasoning",
    "grok-4-1-fast",
    "grok-4-1",
    "grok-4",
    "grok-3",
    "grok-2",
]

XAI_ALIASES = {
    "latest": None,   # Auto-select latest
    "stable": "grok-4-1-fast-reasoning",
}

# Fallback model if API listing fails
XAI_FALLBACK_MODEL = "grok-4-1-fast-reasoning"


def is_grok_search_capable(model_id: str) -> bool:
    """Check if a grok model supports x_search tool.

    Models must be base grok models (not fine-tuned, not embedding).
    """
    if not model_id.startswith("grok"):
        return False
    exclude_patterns = ["embed", "vision", "finetuned"]
    return not any(p in model_id.lower() for p in exclude_patterns)


def list_xai_models(api_key: str) -> List[Dict[str, Any]]:
    """List available xAI models.

    Args:
        api_key: xAI API key

    Returns:
        List of model dicts
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    try:
        response = http.get(XAI_MODELS_URL, headers=headers, timeout=15)
        return response.get("data", [])
    except http.HTTPError as e:
        _log(f"Failed to list xAI models: {e}")
        return []


def select_xai_model(
    api_key: str,
    policy: str = "latest",
    pin: Optional[str] = None,
    mock_models: Optional[List[Dict]] = None,
) -> str:
    """Select the best xAI model for x_search.

    Args:
        api_key: xAI API key
        policy: 'latest' or 'stable'
        pin: Optional model to pin to
        mock_models: Mock model list for testing

    Returns:
        Model ID string
    """
    if pin:
        return pin

    if policy == "stable":
        return XAI_ALIASES["stable"]

    # Check cache
    cached = cache.get_cached_model("xai")
    if cached:
        return cached

    # Fetch available models
    if mock_models is not None:
        models = mock_models
    else:
        models = list_xai_models(api_key)

    if not models:
        _log(f"No models found, using fallback: {XAI_FALLBACK_MODEL}")
        return XAI_FALLBACK_MODEL

    # Get model IDs that support search
    available_ids = {m.get("id") for m in models if is_grok_search_capable(m.get("id", ""))}

    # Find best match from preferred list
    for preferred in XAI_PREFERRED_MODELS:
        if preferred in available_ids:
            _log(f"Selected xAI model: {preferred}")
            cache.set_cached_model("xai", preferred)
            return preferred

    _log(f"No preferred model found, using fallback: {XAI_FALLBACK_MODEL}")
    return XAI_FALLBACK_MODEL


def get_models(
    config: Dict[str, str],
    mock_xai_models: Optional[List[Dict]] = None,
) -> Dict[str, Optional[str]]:
    """Select models for all providers.

    Args:
        config: Configuration with API keys and model policies
        mock_xai_models: Mock models for testing

    Returns:
        Dict with 'xai' key mapping to model ID or None
    """
    result = {"xai": None}

    xai_key = config.get("XAI_API_KEY")
    if xai_key:
        result["xai"] = select_xai_model(
            xai_key,
            policy=config.get("XAI_MODEL_POLICY", "latest"),
            pin=config.get("XAI_MODEL_PIN"),
            mock_models=mock_xai_models,
        )

    return result
