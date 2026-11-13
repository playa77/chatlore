# Development setup tasks — playa77/chatlore

Findings from the first full local bring-up of this fork (2026-11-13), written
down so the setup stays reproducible. Each task lists the evidence it comes
from and an acceptance check. Items are ordered by priority; P1 blocks a
trustworthy setup, P2 is hygiene.

**Status (2026-11-13, later the same day): tasks 1–6 are implemented.**
Task 1: bare-sync `uv run --locked mypy src tests` is clean (overrides for
`anthropic`/`google.genai` plus a `finish_reason` guard in `llm_gemini.py`).
Task 2: `doctor` distinguishes valid/rejected keys via the provider's free
endpoint, and `--probe` proves the models live. Task 3: the paid commands warn
when a key is missing and say what runs instead. Task 4: verified — archive
imports without bsdtar already fail with a named-tool message
(`src/chatlore/importers/intake.py`); documented in the task list only. Task 5:
one `### Added` section under Unreleased. Task 6: the persistent-run recipe is
in docs/chat.md. Task 7 stays optional.

## Verified baseline (this machine, 2026-11-13)

| Check | Command | Result |
|---|---|---|
| Locked install | `uv sync --locked` | OK, 87 packages, CPython 3.12.14, uv 0.12.23 |
| Config | `uv run --locked chatlore doctor` | `z-ai/glm-5.3-flash` + `openai/text-embedding-3-small` via OpenRouter, both keys detected |
| Tests | `uv run --locked pytest` | 0 failed; ~16 skips, all env-gated (FalkorDB URL, bsdtar) |
| Lint | `uv run --locked ruff check src tests` | clean |
| Types (with extras) | `uv run --locked --extra anthropic --extra gemini mypy src tests` | clean (82 files) |
| Types (bare sync) | `uv run --locked mypy src tests` | **4 errors** — see task 1 |
| Serve | `chatlore serve` | loopback-only default, `GET /health` → `{"status":"ok","public":false}` |

## Tasks

### P1 — setup guarantee

1. **Dev/CI mypy parity for the optional provider SDKs.** CI runs
   `uv sync --locked --extra anthropic --extra gemini` before `mypy`
   (`.github/workflows/ci.yml`), but a plain `uv sync --locked` (what README
   prescribes) leaves mypy with 4 errors in
   `src/chatlore/llm_anthropic.py:14` and `src/chatlore/llm_gemini.py:100`
   (missing `anthropic` / `google.genai` stubs plus one downstream
   `union-attr`). With the extras installed the file set is clean.
   Options: document the extras as the dev default in README/CONTRIBUTING, or
   add `anthropic` / `google-genai` to the existing
   `[tool.mypy.overrides] ignore_missing_imports` list (pyproject.toml) the
   way `sqlite_vec`/`fastembed`/`falkordb`/`redis` are handled.
   **Accept:** `uv run --locked mypy src tests` exits 0 in a bare
   `uv sync --locked` environment.

2. **`doctor` validates key presence, not key validity.**
   `src/chatlore/cli.py` (`def doctor`) only checks that
   `CHATLORE_LLM_API_KEY` / `CHATLORE_EMBEDDING_API_KEY` are non-empty; a
   typo'd or revoked key passes. Add provider-appropriate validation — for
   OpenRouter a free authenticated key-info request (e.g. `GET /api/v1/key`,
   verify the exact endpoint) distinguishes set/valid/401 without spending
   credits — and optionally a `--probe` flag that makes one real 1-token call
   plus one embedding call, with an explicit "this costs credits" note.
   **Accept:** `doctor` prints separate set/valid/401 states for both keys.

3. **Silent fallback to inherited defaults when `.env` is not found.** The CLI
   loads the nearest `.env` from the working directory upward
   (`load_env_file`, `cli.py`). Launching `chatlore` outside this checkout —
   or with `.env` missing — silently runs on inherited local-FastEmbed
   defaults and a different chat model (README warns about this in prose
   only). Print a loud one-line warning on serve/import/process/extract/ask
   when neither OpenRouter key is set, naming the expected `.env` path.
   **Accept:** running from a directory without `.env` prints the warning;
   presence of the keys silences it.

4. **`bsdtar` availability on this machine.**
   `tests/importers/test_intake.py:185` skips ("needs bsdtar") and CI's Docker
   lane depends on bsdtar inside the image. Verify what happens at runtime
   when an archive is imported with bsdtar absent (clean error vs. crash),
   then either document `libarchive-tools` as an optional dependency for
   archive imports or make the importer degrade with a clear message.
   **Accept:** importing a `.tar.gz` without bsdtar either works or fails
   with a named-missing-tool message; the skipped test runs after installing
   the tool.

### P2 — hygiene

5. **CHANGELOG `[Unreleased]` has two `### Added` sections** (CHANGELOG.md
   lines ~20 and ~32) from the fork edits. Merge them for
   Keep-a-Changelog/semver-header compliance.

6. **No documented way to run the server beyond a foreground shell.** README
   and docs only show bare `chatlore serve`; the process dies with the shell.
   Document a persistent-run recipe for a desktop box (systemd user unit with
   `Restart=on-failure`, or tmux), including log destination and
   stop/restart commands.
   **Accept:** one documented unit/recipe that survives logout and restarts
   the server automatically.

7. **Local FalkorDB parity (optional).** The store contract tests skip
   without `CHATLORE_TEST_FALKORDB_URL`; CI covers them via a FalkorDB
   service. Nothing to fix — install the `falkordb` extra plus a local
   FalkorDB only if full-suite local runs become necessary.

## Runbook (this machine)

```bash
# start (foreground)
uv run --locked chatlore serve --host 127.0.0.1 --port 8000
# health
curl -s http://127.0.0.1:8000/health
# library lives at ~/.chatlore (SQLite; chatlore.db + wal/shm, uploads/, cache/)
```

Current instance at last check (2026-11-13 22:13 CET): pid 3066066, launched
as an agent-session background process — it does **not** survive session end;
use the task-6 recipe for anything durable.

## Monitoring notes

Health endpoint is `GET /health` (not `/api/health`). During the 2026-11-13
session the server was checked per work-turn: process alive, socket bound to
`127.0.0.1:8000`, `/health` 200, RSS ~173 MB, WAL-backed DB in `~/.chatlore`.
Unattended periodic monitoring would need a scheduled job; not configured.
