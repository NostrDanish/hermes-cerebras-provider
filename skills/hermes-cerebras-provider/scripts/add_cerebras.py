#!/usr/bin/env python3
"""Register Cerebras in Hermes providers so the Desktop list shows it.

Reads the public Cerebras model catalog, then writes providers.cerebras.* via
`hermes config set`. Does not change model.provider or model.default, write a
key, or send a completion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

PROVIDER = "cerebras"
BASE_URL = "https://api.cerebras.ai/v1"
PUBLIC_MODELS_URL = "https://api.cerebras.ai/public/v1/models"
PREFERRED_MODELS = ("qwen-3.8-27b", "gpt-oss-120b")
USER_AGENT = "hermes-cerebras-provider/0.1"


def key_env_for(identity: str) -> str:
    """Match Hermes custom endpoint key slots: HERMES_CUSTOM_<SLUG>_API_KEY."""
    slug = re.sub(r"[^A-Z0-9]+", "_", str(identity or "").upper()).strip("_")
    return f"HERMES_CUSTOM_{slug}_API_KEY" if slug else "HERMES_CUSTOM_API_KEY"


def parse_model_ids(payload: object) -> list[str]:
    """Extract unique model IDs from the Cerebras public catalog response."""
    if isinstance(payload, dict):
        items = payload.get("data")
    elif isinstance(payload, list):
        items = payload
    else:
        return []
    if not isinstance(items, list):
        return []

    ids: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            model_id = item.get("id")
        elif isinstance(item, str):
            model_id = item.strip()
        else:
            continue
        if model_id and str(model_id).strip():
            normalized = str(model_id).strip()
            if normalized not in seen:
                ids.append(normalized)
                seen.add(normalized)
    return ids


def probe_public_catalog(timeout: float = 12.0) -> list[str] | None:
    """Return public Cerebras model IDs on HTTP 200 JSON; never sends credentials."""
    req = urllib.request.Request(
        PUBLIC_MODELS_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                return None
            body = response.read()
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    ids = parse_model_ids(payload)
    return ids or None


def pick_model(ids: list[str], override: str | None = None) -> str:
    """Pick a preferred shared-inference model, or validate an explicit choice."""
    if override is not None:
        selected = override.strip()
        if selected not in ids:
            raise ValueError(f"model {selected!r} is not in the live public catalog")
        return selected
    if not ids:
        raise ValueError("public catalog returned no model IDs")
    available = set(ids)
    for preferred in PREFERRED_MODELS:
        if preferred in available:
            return preferred
    return ids[0]


def hermes_bin() -> str:
    found = shutil.which("hermes")
    if not found:
        raise SystemExit("hermes not on PATH")
    return found


def hermes_env(home: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if home:
        env["HERMES_HOME"] = home
    return env


def hermes_get(
    key: str,
    env: dict[str, str],
    *,
    as_json: bool = False,
    allow_unset: bool = False,
) -> str | None:
    cmd = [hermes_bin(), "config", "get", key]
    if as_json:
        cmd.append("--json")
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"hermes config get {key} timed out") from exc
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        if allow_unset and "Config key not set:" in detail:
            return None
        raise SystemExit(f"hermes config get {key} failed: {detail}")
    return proc.stdout.strip()


def hermes_set(key: str, value: str, env: dict[str, str]) -> None:
    try:
        proc = subprocess.run(
            [hermes_bin(), "config", "set", key, value],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"hermes config set {key} timed out") from exc
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise SystemExit(f"hermes config set {key} failed: {detail}")


def snapshot_defaults(env: dict[str, str]) -> tuple[str | None, str | None]:
    return (
        hermes_get("model.provider", env, allow_unset=True),
        hermes_get("model.default", env, allow_unset=True),
    )


def apply_entry(model: str, env: dict[str, str]) -> None:
    fields = {
        f"providers.{PROVIDER}.name": PROVIDER,
        f"providers.{PROVIDER}.api": BASE_URL,
        f"providers.{PROVIDER}.default_model": model,
        f"providers.{PROVIDER}.discover_models": "true",
        f"providers.{PROVIDER}.transport": "chat_completions",
        f"providers.{PROVIDER}.key_env": key_env_for(PROVIDER),
    }
    for key, value in fields.items():
        hermes_set(key, value, env)


def verify(model: str, before: tuple[str | None, str | None], env: dict[str, str]) -> dict:
    raw = hermes_get(f"providers.{PROVIDER}", env, as_json=True)
    if raw is None:
        raise SystemExit(f"provider row providers.{PROVIDER} is missing")
    entry = json.loads(raw)
    expected = {
        "name": PROVIDER,
        "api": BASE_URL,
        "default_model": model,
        "transport": "chat_completions",
        "key_env": key_env_for(PROVIDER),
    }
    mismatches = [key for key, value in expected.items() if entry.get(key) != value]
    if entry.get("discover_models") is not True:
        mismatches.append("discover_models")
    after = snapshot_defaults(env)
    if after != before:
        raise SystemExit(f"default model changed: {before} -> {after}")
    if mismatches:
        raise SystemExit(f"readback mismatch: {mismatches} entry={entry}")
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add Cerebras to the Hermes provider list.")
    parser.add_argument("--apply", action="store_true", help="Write providers.cerebras via hermes config set.")
    parser.add_argument("--model", default="", help="Provider-row model; must be in the live public catalog.")
    parser.add_argument("--home", default="", help="HERMES_HOME for a specific profile. Does not change the process default.")
    args = parser.parse_args(argv)

    ids = probe_public_catalog()
    if not ids:
        raise SystemExit(f"no live Cerebras public model catalog at {PUBLIC_MODELS_URL}")
    try:
        model = pick_model(ids, args.model or None)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"provider {PROVIDER}")
    print(f"base_url {BASE_URL}")
    print(f"model {model}")
    print(f"public_catalog {len(ids)}")
    print(f"key_env {key_env_for(PROVIDER)}")
    if not args.apply:
        print("dry-run (pass --apply to write providers.cerebras only)")
        return 0

    env = hermes_env(args.home.strip() or None)
    before = snapshot_defaults(env)
    apply_entry(model, env)
    entry = verify(model, before, env)
    print("verified")
    print(json.dumps({"providers.cerebras": entry, "model.provider": before[0], "model.default": before[1]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
