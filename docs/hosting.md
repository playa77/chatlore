# Hosting status and inherited demo infrastructure

This phase runs on the owner's machine using the CLI or
`uv run --locked chatlore serve --host 127.0.0.1`. Follow the
[README](../README.md) for installation and the two-key OpenRouter setup.
Public deployment is deferred; this fork does not document an active hosted
demo or promise that any hosting account, secret or release integration exists.

## What the existing Dockerfile does

The inherited image is a public demonstration, not a private remote-only
installation. It:

- installs this checkout's source and locked dependencies;
- loads a synthetic library into the container user's `~/.chatlore-demo`;
- loads/downloads a local FastEmbed model during the build;
- starts `serve --public --uploads --host 0.0.0.0` on port 7860 or `$PORT`;
- serves the web interface, REST API and MCP, including public uploads.

The repository `.env` is not copied into this image. Merely building the image
does not reproduce the configured OpenRouter embedding setup. Substituting a
remote embedding provider at runtime also needs a plan for the demo's existing
local-model vectors. Use the checkout-based local setup for this phase.

## Existing public-mode controls

These describe inherited behavior, not a recommendation to expose the server:

- `--public` enables LLM question quotas: 10 per visitor per hour and 300 per
  day by default (`--questions-per-hour`, `--questions-per-day`). These do not
  cover all embedding calls or upload enrichment, and do not cap dollar spend.
- Public mode trusts forwarded IP headers from any proxy source. It needs a
  controlled proxy boundary before visitor-IP quotas can be relied on.
- `--uploads` gives visitors cookie-associated temporary SQLite libraries.
  `--keep-hours` defaults to 24; expiry is swept periodically. Bearer cookies
  are not user accounts or a full authentication system. MCP uses the server's
  library rather than the visitor's cookie-associated one.
- Upload size defaults to 200 MB (`--max-upload-mb`). Ordinary unpacking has
  size/count/depth checks, with gaps for some formats and nested containers.
- Upload processing embeds and enriches with the server's model credentials.
  `--extract-limit` caps newly extracted passages per upload, not total model
  calls, embedding volume, number of uploads or provider cost.
- A custom header is required for uploads/deletions. This does not authenticate
  API clients. Public MCP disables its private hostname restriction.

The current [security review](security-review.md) records authentication,
hostname validation, spending and input-handling work to revisit before hosting.

## Inherited deployment workflow

`.github/workflows/deploy.yml` runs on version tags or manual dispatch, with
its job conditional on a nonempty repository variable `HF_SPACE`. It uses
`HF_TOKEN`, the `demo` GitHub environment and Hugging Face's CLI to create a
public Docker Space and upload build files. Those settings must be explicitly
configured for this fork; their presence in YAML does not establish deployment.
No current hosting prices, resource guarantees or retention promises are made.

The Deploy workflow and the Docker CI job remain inherited infrastructure.
This documentation change does not run them, alter their triggers or authorize
a deployment. Reassess their configuration when the hosting phase begins.
