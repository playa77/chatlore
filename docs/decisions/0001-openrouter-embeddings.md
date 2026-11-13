# 0001: Separate OpenRouter embedding credentials

Status: accepted, 2026-11-13.

Context: the fork owner requests OpenRouter with z-ai/glm-5.3-flash for chat
and extraction, openai/text-embedding-3-small for embeddings, two keys and no
local inference.

Decision: add an explicit openrouter embedding provider with a fixed HTTPS
OpenRouter endpoint and a required CHATLORE_EMBEDDING_API_KEY. Never inherit
LLM or generic OpenRouter credentials and never fall back to FastEmbed. Keep
upstream's default provider for compatibility; .env.example explicitly selects
the requested remote configuration. Do not make paid startup warm-up requests.

Rationale: explicit selection preserves upstream offline installations while
providing a strict credential boundary for the requested deployment. Sharing
one generic key would defeat the owner's requested separation.

Consequences: text leaves the machine when embedding, including semantic search
queries. A missing embedding key fails closed. Existing local vectors must be
rebuilt with process --reembed. This costs money; no live inference is authorized
or performed during implementation. FastEmbed remains installed for upstream
compatibility but is never loaded by the OpenRouter provider.

Phase scope: the owner confirmed local-machine-only operation on 2026-11-13.
Additional hosting and security hardening is deferred; tracked findings and
review limits are in [the security review](../security-review.md).
