# hermes-cerebras-provider

A Hermes skill that adds [Cerebras Inference](https://www.cerebras.ai/) to the provider list. It is a registration helper, not a model-provider code plugin: Hermes reads the provider row from `providers:` in its config.

The script probes Cerebras' public model catalog, then uses `hermes config set` to create `providers.cerebras`. It does not change your default model, write an API key, or send a completion.

## Install

```bash
hermes skills install NostrDanish/hermes-cerebras-provider/skills/hermes-cerebras-provider
```

## Run

From the installed skill directory:

```bash
python3 scripts/add_cerebras.py          # preview only
python3 scripts/add_cerebras.py --apply  # register providers.cerebras
```

The preview is a dry run. `--apply` prints `verified` only after reading back the row and checking that `model.provider` and `model.default` are unchanged. Use `--model <id>` to select a different model from the live public catalog, or `--home <path>` to target a separate Hermes profile.

## Provider details

- Base URL: `https://api.cerebras.ai/v1`
- Default row model: `qwen-3.8-27b` when it is in the public catalog; otherwise the first catalog model
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
