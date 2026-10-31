"""Offline checks for add_cerebras. No network, Hermes CLI, or secrets."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import call, patch

_SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "hermes-cerebras-provider" / "scripts" / "add_cerebras.py"
_spec = importlib.util.spec_from_file_location("add_cerebras", _SCRIPT)
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class AddCerebrasTests(unittest.TestCase):
    def test_key_env_matches_desktop_custom_slot(self):
        self.assertEqual(mod.key_env_for("cerebras"), "HERMES_CUSTOM_CEREBRAS_API_KEY")

    def test_catalog_url_and_base_url_are_official(self):
        self.assertEqual(mod.BASE_URL, "https://api.cerebras.ai/v1")
        self.assertEqual(mod.PUBLIC_MODELS_URL, "https://api.cerebras.ai/public/v1/models")

    def test_parse_public_catalog_and_deduplicate(self):
        payload = {"object": "list", "data": [{"id": "qwen-3.8-27b"}, {"id": "gpt-oss-120b"}, {"id": "qwen-3.8-27b"}]}
        self.assertEqual(mod.parse_model_ids(payload), ["qwen-3.8-27b", "gpt-oss-120b"])

    def test_parse_rejects_invalid_shapes(self):
        self.assertEqual(mod.parse_model_ids({"data": "not-a-list"}), [])
        self.assertEqual(mod.parse_model_ids(None), [])

    def test_pick_prefers_qwen_when_available(self):
        self.assertEqual(mod.pick_model(["gpt-oss-120b", "qwen-3.8-27b"]), "qwen-3.8-27b")

    def test_pick_falls_back_to_first_catalog_model(self):
        self.assertEqual(mod.pick_model(["new-model", "other-model"]), "new-model")

    def test_model_override_must_be_in_catalog(self):
        self.assertEqual(mod.pick_model(["qwen-3.8-27b"], "qwen-3.8-27b"), "qwen-3.8-27b")
        with self.assertRaises(ValueError):
            mod.pick_model(["qwen-3.8-27b"], "not-listed")

    def test_probe_uses_public_catalog_without_auth_header(self):
        body = json.dumps({"data": [{"id": "qwen-3.8-27b"}]}).encode()
        with patch.object(mod.urllib.request, "urlopen", return_value=_FakeResponse(body)) as urlopen:
            self.assertEqual(mod.probe_public_catalog(), ["qwen-3.8-27b"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, mod.PUBLIC_MODELS_URL)
        self.assertIsNone(request.get_header("Authorization"))

    def test_apply_writes_only_provider_settings(self):
        env = {"HERMES_HOME": "/profile"}
        with patch.object(mod, "hermes_set") as set_value:
            mod.apply_entry("qwen-3.8-27b", env)
        self.assertEqual(
            set_value.call_args_list,
            [
                call("providers.cerebras.name", "cerebras", env),
                call("providers.cerebras.api", "https://api.cerebras.ai/v1", env),
                call("providers.cerebras.default_model", "qwen-3.8-27b", env),
                call("providers.cerebras.discover_models", "true", env),
                call("providers.cerebras.transport", "chat_completions", env),
                call("providers.cerebras.key_env", "HERMES_CUSTOM_CEREBRAS_API_KEY", env),
            ],
        )

    def test_hermes_get_timeout_is_reported(self):
        with patch.object(mod, "hermes_bin", return_value="hermes"):
            with patch.object(mod.subprocess, "run", side_effect=mod.subprocess.TimeoutExpired("hermes", 30)):
                with self.assertRaisesRegex(SystemExit, "config get model.default timed out"):
                    mod.hermes_get("model.default", {})

    def test_hermes_set_timeout_is_reported(self):
        with patch.object(mod, "hermes_bin", return_value="hermes"):
            with patch.object(mod.subprocess, "run", side_effect=mod.subprocess.TimeoutExpired("hermes", 30)):
                with self.assertRaisesRegex(SystemExit, "config set providers.cerebras.api timed out"):
                    mod.hermes_set("providers.cerebras.api", "https://api.cerebras.ai/v1", {})

    def test_snapshot_defaults_allows_unset_values(self):
        with patch.object(mod, "hermes_get", side_effect=[None, None]) as get:
            self.assertEqual(mod.snapshot_defaults({}), (None, None))
        self.assertEqual(
            get.call_args_list,
            [
                call("model.provider", {}, allow_unset=True),
                call("model.default", {}, allow_unset=True),
            ],
        )

    def test_verify_checks_entry_and_preserves_defaults(self):
        entry = {
            "name": "cerebras",
            "api": "https://api.cerebras.ai/v1",
            "default_model": "qwen-3.8-27b",
            "discover_models": True,
            "transport": "chat_completions",
            "key_env": "HERMES_CUSTOM_CEREBRAS_API_KEY",
        }
        with patch.object(mod, "hermes_get", side_effect=[json.dumps(entry), "nous", "free-model"]):
            result = mod.verify("qwen-3.8-27b", ("nous", "free-model"), {})
        self.assertEqual(result, entry)

    def test_verify_fails_when_default_changes(self):
        entry = {
            "name": "cerebras",
            "api": mod.BASE_URL,
            "default_model": "qwen-3.8-27b",
            "discover_models": True,
            "transport": "chat_completions",
            "key_env": mod.key_env_for("cerebras"),
        }
        with patch.object(mod, "hermes_get", side_effect=[json.dumps(entry), "cerebras", "qwen-3.8-27b"]):
            with self.assertRaises(SystemExit):
                mod.verify("qwen-3.8-27b", ("nous", "free-model"), {})


if __name__ == "__main__":
    unittest.main()
