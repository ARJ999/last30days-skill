"""Environment and configuration management for last30days skill."""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

CONFIG_DIR = Path.home() / ".config" / "last30days"
ENV_FILE = CONFIG_DIR / ".env"


def load_env_file(path: Path = ENV_FILE) -> Dict[str, str]:
    """Load key=value pairs from .env file.

    Args:
        path: Path to .env file

    Returns:
        Dict of key-value pairs
    """
    result = {}
    if not path.exists():
        return result

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                result[key] = value

    return result


def get_config() -> Dict[str, str]:
    """Load configuration from env file and environment.

    Priority: environment variables > .env file

    Returns:
        Config dict with all known keys
    """
    config = load_env_file()

    # Environment variables override .env
    env_keys = [
        "BRAVE_API_KEY",
        "XAI_API_KEY",
        "XAI_MODEL_POLICY",
        "XAI_MODEL_PIN",
        # Legacy keys (for migration detection)
        "OPENAI_API_KEY",
    ]

    for key in env_keys:
        val = os.environ.get(key)
        if val:
            config[key] = val

    return config


def get_available_sources(config: Dict[str, str]) -> str:
    """Determine available sources based on API keys.

    Args:
        config: Configuration dict

    Returns:
        Source availability: 'full', 'brave', 'x', or 'hn'
    """
    has_brave = bool(config.get("BRAVE_API_KEY"))
    has_xai = bool(config.get("XAI_API_KEY"))

    if has_brave and has_xai:
        return "full"      # All sources: Reddit + X + HN + News + Web + Videos
    elif has_brave:
        return "brave"     # Reddit + HN + News + Web + Videos (no X)
    elif has_xai:
        return "x"         # X + HN only
    else:
        return "hn"        # HN only (free, always available)


def validate_sources(
    requested: str,
    available: str,
) -> Tuple[str, Optional[str]]:
    """Validate requested sources against available API keys.

    Args:
        requested: Requested source mode (auto, reddit, x, news, web, all)
        available: Available sources from get_available_sources()

    Returns:
        Tuple of (resolved_sources, error_message_or_None)
    """
    if requested == "auto":
        if available == "full":
            return "full", None
        elif available == "brave":
            return "brave", None
        elif available == "x":
            return "x", None
        else:
            return "hn", None

    if requested == "all":
        if available == "full":
            return "full", None
        elif available == "brave":
            return "brave", "XAI_API_KEY not set. Running without X/Twitter."
        elif available == "x":
            return "x", "BRAVE_API_KEY not set. Running X + HN only."
        else:
            return "hn", "No API keys set. Running HN only."

    if requested == "reddit":
        if available in ("full", "brave"):
            return "reddit", None
        return "hn", "BRAVE_API_KEY required for Reddit search."

    if requested == "x":
        if available in ("full", "x"):
            return "x", None
        return "hn", "XAI_API_KEY required for X/Twitter search."

    if requested == "news":
        if available in ("full", "brave"):
            return "news", None
        return "hn", "BRAVE_API_KEY required for News search."

    if requested == "web":
        if available in ("full", "brave"):
            return "web", None
        return "hn", "BRAVE_API_KEY required for Web search."

    return "hn", f"Unknown source mode: {requested}"


def get_missing_keys(config: Dict[str, str]) -> str:
    """Determine which API keys are missing for promo messaging.

    Returns:
        'both', 'brave', 'x', or 'none'
    """
    has_brave = bool(config.get("BRAVE_API_KEY"))
    has_xai = bool(config.get("XAI_API_KEY"))

    if not has_brave and not has_xai:
        return "both"
    elif not has_brave:
        return "brave"
    elif not has_xai:
        return "x"
    else:
        return "none"


def check_legacy_config(config: Dict[str, str]) -> Optional[str]:
    """Check for legacy OpenAI config and return migration message.

    Returns:
        Migration message or None
    """
    if config.get("OPENAI_API_KEY") and not config.get("BRAVE_API_KEY"):
        return (
            "[MIGRATION] Your config uses OPENAI_API_KEY which is no longer needed.\n"
            "Replace it with BRAVE_API_KEY for superior research capabilities.\n"
            "Get your key at: https://api-dashboard.search.brave.com\n"
            f"Edit: {ENV_FILE}"
        )
    return None
