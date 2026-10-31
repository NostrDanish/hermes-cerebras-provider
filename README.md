# hermes-cerebras-provider

A Hermes skill that adds [Cerebras Inference](https://www.cerebras.ai/) to the provider list. It is a registration helper, not a model-provider code plugin: Hermes reads the provider row from `providers:` in its config.

The helper only lists Cerebras' public model catalog and suggests a current row model. The skill then uses `hermes config set` to create `providers.cerebras`. It does not change your active model, write an API key, or send a completion.

## Install

```bash
hermes skills install NostrDanish/hermes-cerebras-provider/skills/hermes-cerebras-provider
```

## Run

From the installed skill directory:

```bash
python3 scripts/list_models.py  # read-only catalog discovery
```

Choose the suggested model ID from the output, then register the row with the Hermes CLI. Replace the example model ID below if the helper suggests another one:

```bash
hermes config set providers.cerebras.name cerebras
hermes config set providers.cerebras.api https://api.cerebras.ai/v1
hermes config set providers.cerebras.default_model qwen-3.8-27b
hermes config set providers.cerebras.discover_models true
hermes config set providers.cerebras.transport chat_completions
hermes config set providers.cerebras.key_env HERMES_CUSTOM_CEREBRAS_API_KEY
```

Read the provider row back and confirm `model.provider` and `model.default` still match their pre-registration values. Use `HERMES_HOME` on each Hermes CLI command when targeting a separate profile.

## Provider details

- Base URL: `https://api.cerebras.ai/v1`
- Helper: `python3 scripts/list_models.py` (read-only catalog discovery)
- Auth slot: `HERMES_CUSTOM_CEREBRAS_API_KEY`
- API mode: OpenAI-compatible Chat Completions

The script calls `https://api.cerebras.ai/public/v1/models`, which does not require authentication. The inference API's `/v1/models` endpoint requires a valid key. Add your key locally through Hermes provider settings or the active profile's `.env`; never paste it into chat. The provider row has model discovery enabled, so Hermes can query the authenticated catalog after the key is configured.

No completion is sent by this skill. Do not use an inference request as a setup test; free-trial quota and usage are limited and may incur charges.

## Test

The tests use only the Python standard library and make no network or Hermes calls:

```bash
python3 -m unittest discover -s tests -v
```

## Sources

- [Cerebras OpenAI compatibility](https://inference-docs.cerebras.ai/resources/openai)
- [Cerebras public models endpoint](https://inference-docs.cerebras.ai/api-reference/models/public-models)
- [Cerebras Inference Cloud](https://cloud.cerebras.ai/)

## License

MIT
