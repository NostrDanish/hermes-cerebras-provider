---
name: hermes-cerebras-provider
description: Register Cerebras as a Hermes provider row.
version: 0.1.0
author: NostrDanish, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cerebras, hermes, provider, inference]
---

# Hermes Cerebras Provider

Registers Cerebras as a named provider row so it appears in Hermes Desktop's provider list. This is a skill, not a model-provider code plugin. It probes Cerebras' public model catalog, writes only `providers.cerebras` through `hermes config set`, and never changes the active model, stores a key, or sends a completion.

## When to Use

- Add Cerebras Inference to the Hermes provider list.
- Re-register the Cerebras provider row after changing profiles.

Don't use for: switching the default model, adding a fallback, or testing inference.

## Prerequisites

- `hermes` on `PATH` (`hermes config get` / `hermes config set`).
- Python 3.10+ and network access to Cerebras' public model catalog.
- No API key is needed to register the row. Never paste an API key into chat.

## How to Run

From the installed skill directory, preview the live catalog first:

`terminal(command="python3 scripts/add_cerebras.py", workdir="<skill dir>", timeout=60)`

Apply only after the preview shows a current model:

`terminal(command="python3 scripts/add_cerebras.py --apply", workdir="<skill dir>", timeout=60)`

The script prints `verified` only after it reads the provider row back and confirms `model.provider` and `model.default` did not change.

## Procedure

1. Run the script without `--apply`. Confirm it reports the official base URL, a model in the public catalog, and the expected key slot.
2. Run with `--apply`. Done when it prints `verified` and the JSON readback contains `providers.cerebras`.
3. Reopen the provider picker. To use inference, add your own key locally using the slot `HERMES_CUSTOM_CEREBRAS_API_KEY` in Hermes provider settings or the active profile's `.env` file. Do not send the key in chat.

## Pitfalls

- Hermes Desktop reads named provider rows from `providers:` in config; a model-provider plugin alone does not create this row.
- The authenticated `GET https://api.cerebras.ai/v1/models` requires a key. This script instead probes `https://api.cerebras.ai/public/v1/models` and does not send credentials.
- The row enables model discovery against the authenticated inference API. Add a valid key before expecting that catalog to load in Hermes.
- The public catalog covers shared-inference models; dedicated-inference deployments can require an organization-specific endpoint/model ID and are outside this script's scope.
- Do not send a completion as a verification test. Trial credits and usage may be billable or quota-limited.
- Other profiles have separate provider rows. Use `--home <HERMES_HOME>` to target a specific profile; this does not change the default profile.
- Reopen an already-open provider picker to refresh its view.

## Verification

- `hermes config get providers.cerebras --json` shows `name`, `api`, `default_model`, `discover_models: true`, `transport: chat_completions`, and `key_env: HERMES_CUSTOM_CEREBRAS_API_KEY`.
- `model.provider` and `model.default` are unchanged from before the apply.
- No key was written and no inference request was sent.
