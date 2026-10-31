#!/usr/bin/env python3
"""List model IDs from Cerebras' unauthenticated public catalog."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

BASE_URL = "https://api.cerebras.ai/v1"
PUBLIC_MODELS_URL = "https://api.cerebras.ai/public/v1/models"
KEY_ENV = "HERMES_CUSTOM_CEREBRAS_API_KEY"
PREFERRED_MODELS = ("qwen-3.8-27b", "gpt-oss-120b")
USER_AGENT = "hermes-cerebras-provider/0.1"
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


def parse_model_ids(payload: object) -> list[str]:
    """Extract unique, printable model IDs from the public catalog response."""
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
        model_id = item.get("id") if isinstance(item, dict) else item
        if not isinstance(model_id, str):
            continue
        normalized = model_id.strip()
        if _MODEL_ID_RE.fullmatch(normalized) and normalized not in seen:
            ids.append(normalized)
            seen.add(normalized)
    return ids


def probe_public_catalog(timeout: float = 12.0) -> list[str] | None:
    """Fetch public Cerebras model IDs without sending credentials."""
    request = urllib.request.Request(
        PUBLIC_MODELS_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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


def recommended_model(ids: list[str]) -> str | None:
    """Prefer a stable shared-inference model when present; otherwise use the first ID."""
    available = set(ids)
    for preferred in PREFERRED_MODELS:
        if preferred in available:
            return preferred
    return ids[0] if ids else None


def main() -> int:
    ids = probe_public_catalog()
    if not ids:
        raise SystemExit(f"no live Cerebras public model catalog at {PUBLIC_MODELS_URL}")

    print(f"Inference API: {BASE_URL}")
    print(f"Auth environment slot: {KEY_ENV}")
    print("Public catalog models:")
    for model_id in ids:
        print(f"- {model_id}")
    print(f"Suggested default_model: {recommended_model(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
