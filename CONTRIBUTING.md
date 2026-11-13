# Contributing to this fork

Work against [playa77/chatlore](https://github.com/playa77/chatlore). The current
phase is local-machine use with SQLite and two OpenRouter keys, as described in
[the README](README.md). Hosting hardening remains deferred in the
[security review](docs/security-review.md).

## Development setup

Requirements: Git and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/playa77/chatlore.git
cd chatlore
uv sync --locked --extra anthropic --extra gemini
uv run --locked chatlore --help
```

The extras provide the SDKs exercised by CI; they do not select those providers
or enable local inference. `uv sync` installs the development dependency group
by default. Ordinary users can omit the extras. Keep dependency resolution
pinned with `--locked`; use `uv lock` intentionally when changing dependencies.

For application use, copy `.env.example` to `.env` once and fill in keys locally.
No real keys or live inference are needed for the standard test suite. Tests use
synthetic fixtures and mocked clients; optional FalkorDB integration cases need
a separate server and are skipped when it is absent.

## Checks

Run the same Python checks configured in CI:

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest
```

`uv run --locked ruff format .` applies formatting. The optional pre-commit hooks
can be installed with `uv run --locked pre-commit install`.

CI also defines package, inherited demo/Docker and FalkorDB jobs. Their existence
does not establish that hosted deployment is configured or approved for this
fork. Do not run live model tests with developer-agent credentials.

## Branches and pull requests

Use `feat/<topic>`, `fix/<topic>`, `docs/<topic>` or `chore/<topic>` branches and
open pull requests against this fork's `main`. Use Conventional Commits, for
example `docs: refresh fork installation and model setup`. Keep each change
focused, update `CHANGELOG.md` under Unreleased, and fill in the repository's
PR template with checks actually run and relevant limitations.

Do not assume branch protection, squash-only merges, PyPI publishing or hosting
credentials have been configured merely because inherited workflows exist.
See [releasing.md](docs/releasing.md) before any release work.

## Privacy and documentation

Never commit real chat exports, databases or keys. The `.gitignore` excludes
`exports/`, `.chatlore/` and `.env` files; verify staged paths before committing.
Fixtures under `tests/fixtures/` are synthetic.

Document installation from this fork, use checkout-based command examples, and
distinguish the `.env.example` configuration from inherited code defaults.
Preserve upstream attribution and historical changelog entries. Avoid carrying
upstream benchmarks forward as performance or pricing promises for this fork.
