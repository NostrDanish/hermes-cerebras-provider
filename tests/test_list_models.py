"""Offline checks for the read-only Cerebras model-list helper."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

_SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "hermes-cerebras-provider" / "scripts" / "list_models.py"
_spec = importlib.util.spec_from_file_location("list_cerebras_models", _SCRIPT)
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class ListCerebrasModelsTests(unittest.TestCase):
    def test_catalog_urls_and_key_slot(self):
        self.assertEqual(mod.BASE_URL, "https://api.cerebras.ai/v1")
        self.assertEqual(mod.PUBLIC_MODELS_URL, "https://api.cerebras.ai/public/v1/models")
        self.assertEqual(mod.KEY_ENV, "HERMES_CUSTOM_CEREBRAS_API_KEY")

    def test_parse_public_catalog_and_deduplicate(self):
        payload = {
            "object": "list",
            "data": [
                {"id": "qwen-3.8-27b"},
                {"id": "gpt-oss-120b"},
                "qwen-3.8-27b",
            ],
        }
        self.assertEqual(mod.parse_model_ids(payload), ["qwen-3.8-27b", "gpt-oss-120b"])

    def test_parse_rejects_invalid_shapes_and_unsafe_ids(self):
        self.assertEqual(mod.parse_model_ids({"data": "not-a-list"}), [])
        self.assertEqual(mod.parse_model_ids(None), [])
        self.assertEqual(mod.parse_model_ids({"data": [{"id": "\x1b[31mBAD"}, {"id": ""}]}), [])

    def test_recommends_qwen_when_available(self):
        self.assertEqual(mod.recommended_model(["gpt-oss-120b", "qwen-3.8-27b"]), "qwen-3.8-27b")

    def test_recommendation_falls_back_to_first_catalog_model(self):
        self.assertEqual(mod.recommended_model(["new-model", "other-model"]), "new-model")

    def test_empty_catalog_has_no_recommendation(self):
        self.assertIsNone(mod.recommended_model([]))

    def test_probe_uses_public_catalog_without_auth_header(self):
        body = json.dumps({"data": [{"id": "qwen-3.8-27b"}]}).encode()
        with patch.object(mod.urllib.request, "urlopen", return_value=_FakeResponse(body)) as urlopen:
            self.assertEqual(mod.probe_public_catalog(), ["qwen-3.8-27b"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, mod.PUBLIC_MODELS_URL)
        self.assertIsNone(request.get_header("Authorization"))

    def test_probe_rejects_non_200(self):
        with patch.object(mod.urllib.request, "urlopen", return_value=_FakeResponse(b"{}", status=503)):
            self.assertIsNone(mod.probe_public_catalog())

    def test_probe_handles_network_and_json_errors(self):
        with patch.object(mod.urllib.request, "urlopen", side_effect=mod.urllib.error.URLError("offline")):
            self.assertIsNone(mod.probe_public_catalog())
        with patch.object(mod.urllib.request, "urlopen", return_value=_FakeResponse(b"not json")):
            self.assertIsNone(mod.probe_public_catalog())


if __name__ == "__main__":
    unittest.main()
