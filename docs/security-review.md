# Security review — 2026-11-13

Scope: source in this checkout, model clients, import/archive boundaries,
REST/MCP exposure, web rendering, dependencies and build/release configuration.
This is a code review with synthetic local tests, not a security certification.
No real keys, private exports, or live inference were used.

Verdict: no obvious deliberate key-exfiltration or telemetry path was found in
the reviewed application code. There are security defects and operational risks;
do not treat this as safe for public hosting or hostile input.

## Current phase and deferred work

The owner confirmed on 2026-11-13 that this phase runs only on their own machine.
The deployment target is the local CLI and a loopback-bound server with the
explicit OpenRouter configuration. Public hosting, authentication, network cost
controls and additional import hardening are deferred to a later phase. The
findings below remain recorded for that work; they are not release blockers for
this agreed local-only phase. Local input-handling risks still apply when
importing untrusted files. Revisit this review before expanding deployment scope.

## Findings

1. **High: archive conversation IDs allow writes outside the library (fixed).**
   `Conversation.id` was only checked for nonempty text. `Library.path_for`
   interpolated it directly into a filename; `import_archive` accepts these IDs
   from `conversations.jsonl`. IDs with `../` or absolute paths could write JSON
   records outside the library with the process's permissions. The fix rejects
   path separators, NUL and colon, and checks the resolved path stays inside the
   library. Regression tests cover POSIX and Windows forms. This does not make
   arbitrary archives trusted or protect against concurrent hostile local users.

2. **High when reachable: unauthenticated library API and missing REST Host checks
   (unresolved).** Ordinary REST routes do not require authentication or validate
   Host. With a synthetic nonempty library, a TestClient GET to `/library/export`
   using base URL `http://attacker.example` returned HTTP 200 and a ZIP without
   credentials. This verifies the missing server-side check, not an end-to-end
   browser DNS rebinding exploit. MCP's transport protections do not cover REST.
   A DNS rebinding attack may expose localhost data where browser/network defenses
   allow it. Keep the service stopped when unused; localhost binding limits LAN
   access but does not replace Host validation. Any network deployment needs an
   authenticated proxy and Host/Origin checks for REST and MCP.

3. **High for public paid deployments: incomplete cost controls (unresolved).**
   Uploads automatically embed and extract using server keys. Public question
   quotas do not cap upload processing, semantic search, or MCP embeddings.
   `/chat` embeds the query before checking its question allowance. The public
   CLI trusts all forwarded client IP headers, so a directly reachable instance
   can accept spoofed visitor identity. The Dockerfile enables public uploads
   and downloads a local model during build. Do not use it for a private BYOK
   library. Key credit limits are essential; request counts are not dollar caps.

4. **Medium: folder imports read symlink targets (unresolved).** A synthetic
   `input/linked.txt` symlink pointing outside the selected directory was imported
   successfully. `os.walk` does not follow directory symlinks by default, but file
   paths and specially recognized export files are opened normally. A malicious
   supplied folder could therefore pull extra local text into the library and
   subsequent remote model processing. Import only trusted, inspected folders.

5. **Medium: decompression limits have gaps (unresolved).** ChatLore archives
   bypass Intake's normal unpack reservation. `archive.read(manifest.json)`,
   JSONL reads and cache restoration lack an aggregate expanded-byte limit.
   Office/EPUB ZIP readers limit compressed document size, not aggregate expanded
   content. bsdtar's listing estimates and extraction are separate steps, with
   no process timeout or runtime byte enforcement. Existing ZIP/TAR traversal
   protection and ordinary unpack limits are useful but insufficient for hostile
   uploads. Possible consequences include memory/disk exhaustion and stalled
   workers. No large decompression bomb was executed.

6. **Medium: error and configuration handling can expose sensitive data
   (partially mitigated for the new client).** LLM errors include provider response
   messages and configured URLs, which may echo user input or contain URL secrets.
   The nearest parent `.env` is automatically loaded by the CLI. Generic
   `CHATLORE_LLM_API_KEY` follows the configured endpoint; the fallback
   `OPENROUTER_API_KEY` hostname test also accepts HTTP and OpenRouter subdomains.
   Use the exact HTTPS endpoint from the template and launch from a trusted
   directory. The new embedding client uses a fixed HTTPS endpoint, requires its
   own key, and exposes only status codes on provider failures.

## Positive observations and limits

- SQLite queries generally bind data parameters. YAML parsing uses safe_load.
  No application eval/pickle loading or shell=True execution was found.
- The web Markdown renderer escapes text before adding its small set of markup;
  scripts/styles are served locally, without a third-party JavaScript CDN.
- Import/delete endpoints require a custom header and no permissive CORS setup
  was found. This does not supply authentication or prevent DNS rebinding.
- Library archives explicitly export conversations, graph data and model caches,
  not `.env` files. Those exports still contain private plaintext data.
- The lockfile records PyPI sources and hashes. CI has read-only default token
  permissions; release jobs gain scoped publishing permissions. Actions and base
  images use mutable version tags rather than immutable commit/digest pins.
  Broad lower-bound dependencies can resolve differently without the lockfile.
- Dependency source code, package registry ownership, published binary integrity,
  current vulnerability advisories, Docker builds and FalkorDB operation were
  not independently verified. No claim is made that dependencies are free of
  vulnerabilities. Use `uv sync --locked` for this checkout.
- Model identifiers, current availability, pricing and GLM reasoning behavior
  were not verified against live OpenRouter. Mocked HTTP tests verify request
  shape and key isolation only. No API keys are required for these tests.

## Delivered configuration

`.env.example` selects the owner's requested models and separate keys. It keeps
upstream local defaults available for compatibility, so the template must be
active for every launch to guarantee remote-only operation. Never use developer
agent credentials for the application. See `docs/models.md` and decision 0001.

## Verification

The full local suite passed: 421 passed, 22 skipped (optional/integration cases).
Ruff lint and formatting, mypy and `git diff --check` passed. Added mocked
embedding tests cover the fixed endpoint, dedicated key requirement, wire
format, vector ordering/validation and sanitized failures without retries.
Library tests cover traversal IDs. Docker, browser exploitability and live
provider behavior remain unverified.
