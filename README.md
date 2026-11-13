# ChatLore — playa77 fork

> All your AI conversations, one graph, one chat.

[![CI](https://github.com/playa77/chatlore/actions/workflows/ci.yml/badge.svg)](https://github.com/playa77/chatlore/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

This fork of [cl0ver012/chatlore](https://github.com/cl0ver012/chatlore) imports
AI conversations and documents into a local library, builds a knowledge graph,
and provides search and chat with sources through a CLI, web interface and MCP.
It is pre-alpha.

The current phase runs on your own machine with SQLite and **two OpenRouter
keys**, using `z-ai/glm-5.3-flash` for chat/extraction and
`openai/text-embedding-3-small` for embeddings. No local model runs with the
configuration below. Library files stay on disk; model processing sends text
to OpenRouter and its serving providers. See [model settings](docs/models.md).

## Install this fork

Requirements: Git and [uv](https://docs.astral.sh/uv/). uv manages the project's
Python version. Run these commands in a terminal:

```bash
git clone https://github.com/playa77/chatlore.git
cd chatlore
uv sync --locked
```

Use `uv run --locked chatlore` from this checkout for the commands below. Bare
package-name installs from PyPI install the upstream distribution, not this fork.
There is no separate fork PyPI release configured by these instructions.

## Configure the two keys

Copy the template once, without overwriting an existing configuration:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead. Edit `.env`
locally and fill in `CHATLORE_LLM_API_KEY` and `CHATLORE_EMBEDDING_API_KEY` with
two separate OpenRouter keys. Keep the provider, endpoint and model settings
from the template. `.env` is ignored by Git; never commit real keys.

```bash
uv run --locked chatlore doctor
```

Check that it reports the two models above, embeddings via `openrouter`, and
both keys set — and, since it asks the provider, that both keys are accepted.
`--probe` also sends one tiny request to each model to prove the whole path;
that spends a little credit. Shell environment variables override `.env`. The CLI loads the
nearest `.env` in or above its working directory, so keep launching from this
checkout. Without the template, inherited code defaults still select local
FastEmbed embeddings and a different chat model.

## Import, search and ask

```bash
uv run --locked chatlore import path/to/your-export.zip
uv run --locked chatlore search "postgres index"             # local word search
uv run --locked chatlore process                             # paid remote embeddings
uv run --locked chatlore search "why was my query slow" --semantic
uv run --locked chatlore search "slow postgres query" --hybrid
uv run --locked chatlore extract --limit 10 --workers 1       # paid graph enrichment
uv run --locked chatlore topics
uv run --locked chatlore entity "postgres"
uv run --locked chatlore facts "backups"
uv run --locked chatlore ask "why was my query slow?"         # paid retrieval/chat
uv run --locked chatlore serve --host 127.0.0.1               # http://127.0.0.1:8000
```

`--limit` limits new extraction chunks, not the cost of all enrichment stages.
Set spending limits on both OpenRouter keys. Semantic and hybrid queries can
make embedding requests. Web uploads automatically import, embed and enrich;
the CLI separates these steps so you can start with word search alone.

The library defaults to `~/.chatlore`; put `--home <folder>` before a command
or set `CHATLORE_HOME` to change it. Importing the same data again updates changed
conversations. Back up with `uv run --locked chatlore export chatlore.zip`.
If migrating vectors from another model, back up first and run
`uv run --locked chatlore process --reembed` to rebuild them at provider cost.

## Guides

- [Models, credentials and data flow](docs/models.md)
- [Import formats and processing](docs/importers.md)
- [Graph extraction and caching](docs/extraction.md)
- [Chat and REST API](docs/chat.md)
- [Web interface](docs/web.md)
- [MCP for local assistants](docs/mcp.md)
- [Backups and Markdown export](docs/export.md)
- [Security review and deferred work](docs/security-review.md)
- [Inherited hosting/demo infrastructure](docs/hosting.md)
- [Optional FalkorDB backend](docs/falkordb.md)
- [Development](CONTRIBUTING.md) and [release status](docs/releasing.md)

The bundled demo uses an inherited local embedding model. `chatlore demo` and
the Dockerfile are not the remote-only onboarding path. Public hosting and
additional security hardening are deferred; the current target is a local CLI
and loopback-bound server.

## Development and updates

Follow [CONTRIBUTING.md](CONTRIBUTING.md) for the full CI environment. To update
an existing checkout on `main`, preserve your work and local `.env`, then run:

```bash
git pull --ff-only
uv sync --locked
uv run --locked chatlore doctor
```

Check [CHANGELOG.md](CHANGELOG.md) before processing an existing library after
an update. Implemented features include import, word/vector/graph search,
entity and fact extraction, topic reports, cited chat, a web graph explorer,
MCP and archives. A hosted release is not part of this phase.

## License

[MIT](LICENSE). Original copyright and author attribution are retained.
