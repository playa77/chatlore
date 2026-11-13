"""Credential isolation and wire contract for remote embeddings; no live calls."""

from __future__ import annotations

import json
from pathlib import Path

import httpx2
import pytest

from chatlore.embeddings import EmbeddingError, OpenRouterEmbedder, make_embedder


def test_dedicated_key_required_even_with_llm_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.delenv("CHATLORE_EMBEDDING_API_KEY", raising=False)
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "chat-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "generic-key")
    with pytest.raises(EmbeddingError, match="CHATLORE_EMBEDDING_API_KEY"):
        make_embedder(tmp_path)


def test_factory_selects_remote_without_loading_fastembed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("CHATLORE_EMBEDDING_API_KEY", "embedding-only")
    monkeypatch.delenv("CHATLORE_EMBEDDING_MODEL", raising=False)
    embedder = make_embedder(tmp_path)
    assert isinstance(embedder, OpenRouterEmbedder)
    assert embedder.name == "openai/text-embedding-3-small"
    assert embedder.embed_passages([]) == []
    embedder.close()
    assert not (tmp_path / "cache" / "models").exists()


def test_embeddings_wire_contract_and_response_order() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert str(request.url) == "https://openrouter.ai/api/v1/embeddings"
        assert request.headers["authorization"] == "Bearer embedding-only"
        assert json.loads(request.content) == {
            "model": "openai/text-embedding-3-small",
            "input": ["first", "second"],
            "encoding_format": "float",
        }
        return httpx2.Response(
            200,
            json={
                "object": "list",
                "model": "openai/text-embedding-3-small",
                "data": [
                    {"object": "embedding", "index": 1, "embedding": [0.0, 1.0]},
                    {"object": "embedding", "index": 0, "embedding": [1.0, 0.0]},
                ],
                "usage": {"prompt_tokens": 2, "total_tokens": 2},
            },
        )

    client = OpenRouterEmbedder(
        "openai/text-embedding-3-small",
        "embedding-only",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    try:
        assert client.embed_passages(["first", "second"]) == [[1.0, 0.0], [0.0, 1.0]]
    finally:
        client.close()


@pytest.mark.parametrize("status", [401, 429, 500])
def test_errors_are_sanitized_without_retries_or_fallback(status: int) -> None:
    requests = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(status, json={"error": {"message": "private input"}})

    client = OpenRouterEmbedder(
        "openai/text-embedding-3-small",
        "embedding-only",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    try:
        with pytest.raises(EmbeddingError) as caught:
            client.embed_query("private query")
        assert str(status) in str(caught.value)
        assert "private" not in str(caught.value)
        assert len(requests) == 1
    finally:
        client.close()


@pytest.mark.parametrize(
    "indices,vectors",
    [
        ([0, 0], [[1.0], [2.0]]),
        ([1], [[1.0]]),
        ([0], [[]]),
        ([0, 1], [[1.0], [1.0, 2.0]]),
    ],
)
def test_malformed_vectors_are_rejected(indices: list[int], vectors: list[list[float]]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "object": "list",
                "model": "test",
                "data": [
                    {"object": "embedding", "index": i, "embedding": v}
                    for i, v in zip(indices, vectors, strict=True)
                ],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            },
        )

    client = OpenRouterEmbedder(
        "test",
        "embedding-only",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    try:
        with pytest.raises(EmbeddingError):
            client.embed_passages(["text"] * len(indices))
    finally:
        client.close()
