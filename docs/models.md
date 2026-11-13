# Models and OpenRouter credentials

This fork's current setup uses hosted models through OpenRouter. Install from
[this fork's checkout](../README.md#install-this-fork), copy `.env.example` to
`.env` once, and edit the two blank key fields locally. Run examples from the
checkout with `uv run --locked chatlore`.

## Active configuration

| Variable | Template value | Purpose |
|---|---|---|
| `CHATLORE_LLM_PROVIDER` | `openai` | OpenAI-compatible protocol, including OpenRouter |
| `CHATLORE_LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Chat/extraction endpoint |
| `CHATLORE_LLM_MODEL` | `z-ai/glm-5.3-flash` | Chat, extraction, summaries, duplicate checks and topic reports |
| `CHATLORE_LLM_REASONING` | `default` | Send no reasoning override; leave behavior to the model |
| `CHATLORE_LLM_API_KEY` | blank; fill locally | First OpenRouter key, for the LLM |
| `CHATLORE_EMBEDDING_PROVIDER` | `openrouter` | Remote embeddings; no local fallback |
| `CHATLORE_EMBEDDING_MODEL` | `openai/text-embedding-3-small` | Passage and query embeddings |
| `CHATLORE_EMBEDDING_API_KEY` | blank; fill locally | Second OpenRouter key, used only for embeddings |

```bash
uv run --locked chatlore doctor
```

`doctor` reports the selected models and whether keys are set, without printing
the keys. Fill `CHATLORE_LLM_API_KEY` for this setup, even if a diagnostic
also mentions the inherited `OPENROUTER_API_KEY` fallback.

The CLI reads the nearest `.env` in the working directory or a parent directory.
Existing shell variables take precedence, including empty values. Running from
a different folder or using an assistant launcher without a working directory
can select a different configuration. For MCP use the explicit checkout launch
command in [mcp.md](mcp.md). Library location (`--home`/`CHATLORE_HOME`) does not
select the `.env` file.

## Key isolation and request behavior

The embedding client accepts only `CHATLORE_EMBEDDING_API_KEY`. It never borrows
`CHATLORE_LLM_API_KEY` or `OPENROUTER_API_KEY`, uses a fixed HTTPS OpenRouter
endpoint, has a 60 second request timeout and disables automatic retries.
Missing credentials or request errors never switch to a local embedding model.
Server startup does not make a remote embedding warm-up request.

The LLM client uses `CHATLORE_LLM_API_KEY` first, with `OPENROUTER_API_KEY` as a
fallback when the configured hostname matches OpenRouter. The generic LLM key
follows `CHATLORE_LLM_BASE_URL`, so keep the exact HTTPS URL in the template.
The LLM client currently permits two automatic SDK retries and has a 120 second
request timeout; a command making many requests has no overall dollar/time cap.

Use two distinct keys and set their credit limits in OpenRouter. If BYOK means
supplying an upstream provider's own key to OpenRouter, configure that in your
OpenRouter account separately. ChatLore does not provision upstream credentials
or force a particular serving provider.

## What leaves your machine

| Operation | Remote processing in this setup |
|---|---|
| CLI import, note, word search, browsing, archive export/import | No model call |
| `process` | Sends uncached passage text to the embedding model |
| Semantic/hybrid search and MCP retrieval | Sends a query for embedding when vectors exist |
| `extract` | Sends chunks and derived entity/topic text to the LLM |
| `ask` / web chat | Embeds the question when vectors exist; sends the question, retrieved sources and graph context to the LLM when context is found |
| Web upload | Runs import, embedding and graph enrichment automatically |

Files and caches are plaintext locally. Cached vectors can avoid passage calls
when rebuilding with the same model; search queries are not persisted in that
passage cache. See [extraction.md](extraction.md) for enrichment caching.

## First run and changing models

```bash
uv run --locked chatlore import path/to/your-export.zip
uv run --locked chatlore process
uv run --locked chatlore extract --limit 10 --workers 1
uv run --locked chatlore serve --host 127.0.0.1
```

Processing and enrichment cost provider credits. `--limit` caps newly extracted
chunks; summaries, duplicate decisions and topic reports can add calls. Use a
small import first. Live availability, pricing and GLM reasoning behavior have
not been validated for this fork; consult OpenRouter's current model information.
Historical upstream timing/cost figures are not estimates for this setup.

Changing the embedding model requires a backup followed by
`uv run --locked chatlore process --reembed`. This clears old vectors and can
incur new charges. Keep the same embedding model for indexing and retrieval.
Do not mix the bundled demo's local vectors with the OpenRouter configuration.
Changing LLM models can create new enrichment cache misses and costs.

## Inherited alternatives and code defaults

The following remain implemented for compatibility, but are outside the chosen
remote-only setup. These are **code defaults without `.env`**, not the template:

| Setting | Inherited default |
|---|---|
| Embedding provider | `fastembed` (local model, may download weights) |
| Embedding model with FastEmbed | `BAAI/bge-small-en-v1.5` |
| Embedding model with OpenRouter | `openai/text-embedding-3-small` |
| LLM provider | `openai` |
| LLM endpoint | `https://openrouter.ai/api/v1` |
| LLM model | `deepseek/deepseek-v4-flash` |
| LLM reasoning | `off` |

FastEmbed is still a dependency but does not load when the provider is
`openrouter`. There is no need to install a local inference server.

The OpenAI-compatible client also accepts other endpoints. Native Anthropic and
Gemini clients are optional extras; install them **from this checkout** with
`uv sync --locked --extra anthropic` or `uv sync --locked --extra gemini`.
They use `CHATLORE_LLM_PROVIDER=anthropic`/`gemini` and their corresponding
`ANTHROPIC_API_KEY` or `GEMINI_API_KEY`/`GOOGLE_API_KEY` fallback variables.
`CHATLORE_LLM_API_KEY` overrides those too. They do not change the embedding
provider. No native-provider model recommendation is maintained in this phase.

Accepted reasoning settings are `default`, `off`, `low`, `medium` and `high`.
Their support depends on the selected API/model; `default` sends no override.
See [the decision record](decisions/0001-openrouter-embeddings.md) and
[security review](security-review.md) for scope and deferred work.
