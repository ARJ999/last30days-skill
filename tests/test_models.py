"""Tests for models module (xAI only)."""

import sys
import unittest
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import models


class TestIsGrokSearchCapable(unittest.TestCase):
    def test_grok_base_is_capable(self):
        self.assertTrue(models.is_grok_search_capable("grok-4-1"))

    def test_grok_fast_is_capable(self):
        self.assertTrue(models.is_grok_search_capable("grok-4-1-fast"))

    def test_grok_embed_is_not_capable(self):
        self.assertFalse(models.is_grok_search_capable("grok-embed-v1"))

    def test_grok_vision_is_not_capable(self):
        self.assertFalse(models.is_grok_search_capable("grok-vision-v1"))

    def test_grok_reasoning_is_not_capable(self):
        self.assertFalse(models.is_grok_search_capable("grok-3-reasoning"))

    def test_non_grok_is_not_capable(self):
        self.assertFalse(models.is_grok_search_capable("llama-3"))


class TestSelectXAIModel(unittest.TestCase):
    def test_latest_policy(self):
        from lib import cache
        cache.MODEL_CACHE_FILE.unlink(missing_ok=True)
        mock_models = [
            {"id": "grok-4-1-fast", "created": 1704067200},
            {"id": "grok-4-1", "created": 1704067200},
            {"id": "grok-3", "created": 1701388800},
        ]
        result = models.select_xai_model(
            "fake-key",
            policy="latest",
            mock_models=mock_models,
        )
        self.assertEqual(result, "grok-4-1-fast")

    def test_stable_policy(self):
        from lib import cache
        cache.MODEL_CACHE_FILE.unlink(missing_ok=True)
        result = models.select_xai_model(
            "fake-key",
            policy="stable",
        )
        self.assertEqual(result, "grok-4-1-fast")

    def test_pinned_policy(self):
        result = models.select_xai_model(
            "fake-key",
            policy="pinned",
            pin="grok-3",
        )
        self.assertEqual(result, "grok-3")

    def test_fallback_when_no_models(self):
        from lib import cache
        cache.MODEL_CACHE_FILE.unlink(missing_ok=True)
        result = models.select_xai_model(
            "fake-key",
            policy="latest",
            mock_models=[],
        )
        self.assertEqual(result, "grok-4-1-fast")


class TestGetModels(unittest.TestCase):
    def test_no_keys_returns_none(self):
        config = {}
        result = models.get_models(config)
        self.assertIsNone(result["xai"])

    def test_xai_key_selects_model(self):
        from lib import cache
        cache.MODEL_CACHE_FILE.unlink(missing_ok=True)
        config = {"XAI_API_KEY": "xai-test"}
        mock_xai = [
            {"id": "grok-4-1-fast", "created": 1704067200},
            {"id": "grok-4-1", "created": 1704067200},
        ]
        result = models.get_models(config, mock_xai_models=mock_xai)
        self.assertEqual(result["xai"], "grok-4-1-fast")


if __name__ == "__main__":
    unittest.main()
