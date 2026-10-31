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

Registers Cerebras as a named provider row so it appears in Hermes Desktop's provider list. The helper only reads Cerebras' public model catalog; use the Hermes CLI to write provider settings. This skill never changes the active model, stores an API key, or sends an inference completion.

## When to Use

- Add Cerebras Inference to the Hermes provider list.
- Re-register the Cerebras provider row in a profile.

Don't use for: switching the default model, adding a fallback, or testing inference.

## Prerequisites

- `hermes` on `PATH` (`hermes config get` / `hermes config set`).
- Python 3.10+ and network access to Cerebras' public model catalog.
- No API key is needed to register the row. If the user wants inference, they add `HERMES_CUSTOM_CEREBRAS_API_KEY` locally to the active profile's `.env`; never request or write the key in chat.

## How to Run

From the installed skill directory, list available public models:

`terminal(command="python3 scripts/list_models.py", workdir="<skill dir>", timeout=60)`

The helper is read-only. Register the row with the Hermes CLI, not by editing `config.yaml`.

## Procedure

1. Record the current defaults before changing anything:

   `terminal(command="hermes config get model.provider; hermes config get model.default", timeout=20)`

2. Run `scripts/list_models.py`. Use the exact ID printed after `Suggested default_model:` if it is still present in the catalog; otherwise choose another listed ID.

3. Register only `providers.cerebras.*` with `hermes config set`. Replace the example model ID with the selected live ID when needed:

   `terminal(command="hermes config set providers.cerebras.name cerebras && hermes config set providers.cerebras.api https://api.cerebras.ai/v1 && hermes config set providers.cerebras.default_model qwen-3.8-27b && hermes config set providers.cerebras.discover_models true && hermes config set providers.cerebras.transport chat_completions && hermes config set providers.cerebras.key_env HERMES_CUSTOM_CEREBRAS_API_KEY", timeout=60)`

   Done when the command exits 0. If any command fails, stop, report the failing output, and inspect the partial row before retrying.

4. Read the row and defaults back:

   `terminal(command="hermes config get providers.cerebras --json && hermes config get model.provider && hermes config get model.default", timeout=20)`

   Done when the row shows `api`, `default_model`, `discover_models: true`, `transport: chat_completions`, and the expected `key_env`, while both defaults match step 1.

5. Tell the user to reopen the provider picker. If they want to use inference, they add the key themselves to the active profile's `.env`; do not send a completion as a setup test.

## Pitfalls

- Hermes Desktop reads named provider rows from `providers:` in config; a model-provider code plugin alone does not create this row.
- The authenticated `GET https://api.cerebras.ai/v1/models` requires a key. The helper instead queries `https://api.cerebras.ai/public/v1/models` without credentials.
- The row enables model discovery against the authenticated inference API. Add a valid key locally before expecting Hermes to query that catalog.
- The public catalog covers shared-inference models; dedicated deployments can require an organization-specific endpoint or model ID and are outside this helper's scope.
- Do not send an inference completion to verify setup. Trial credits and usage are limited and may be billable.
- Provider rows are profile-scoped. When targeting another profile, set `HERMES_HOME` on each Hermes CLI command; do not change a different profile unless asked.
- Reopen an already-open provider picker to refresh its view.

## Verification

- `hermes config get providers.cerebras --json` shows `name`, `api`, `default_model`, `discover_models: true`, `transport: chat_completions`, and `key_env: HERMES_CUSTOM_CEREBRAS_API_KEY`.
- `model.provider` and `model.default` are unchanged from the recorded values.
- No API key was written and no inference request was sent.
