"""Embedding models and a disk cache for their output.

The fork's template selects remote OpenRouter embeddings with a dedicated key.
Without that configuration, inherited defaults select local FastEmbed (ONNX).
Anything with the ``Embedder`` shape can replace either client.

Passage vectors are cached by model name and text hash in SQLite, so matching
cached inputs can be reused during a graph rebuild. Query calls are not cached
here; missing passage entries still require embedding work.
"""

from __future__ import annotations

import hashlib
import math
import os
import sqlite3
import threading
from array import array
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Self

import openai

from chatlore.llm import OPENROUTER_CREDITS_URL

if TYPE_CHECKING:
    import httpx2

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
MODEL_ENV = "CHATLORE_EMBEDDING_MODEL"


class EmbeddingError(Exception):
    """The embedding model could not be loaded or used."""


class Embedder(Protocol):
    """What the pipeline and search need from an embedding model."""

    name: str

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed stored text."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query. Some models treat queries differently from passages."""
        ...


class FastEmbedEmbedder:
    """Local embeddings through fastembed. The model loads on first use."""

    def __init__(self, model: str = DEFAULT_MODEL, cache_dir: Path | None = None) -> None:
        self.name = model
        self._cache_dir = cache_dir
        self._model: Any = None
        self._loading = threading.Lock()

    def _load(self) -> Any:
        # One load at a time: requests arriving together share one download.
        with self._loading:
            return self._load_once()

    def _load_once(self) -> Any:
        if self._model is None:
            # The Hugging Face native downloader crashes on some Windows machines where
            # security or licensing software injects a DLL into every process. The
            # pure-Python downloader is slower but works everywhere; models are small.
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            try:
                from fastembed import TextEmbedding  # heavy, so loaded on first use
                from loguru import logger  # fastembed's logger

                cache = str(self._cache_dir) if self._cache_dir is not None else None
                # Before the first download, fastembed logs errors about the missing
                # model, which is expected, so they are muted for this attempt.
                logger.disable("fastembed")
                try:
                    # Once the model is on disk, load it without asking the hub anything:
                    # faster, silent, and it keeps search working offline.
                    self._model = TextEmbedding(self.name, cache_dir=cache, local_files_only=True)
                except Exception:
                    logger.enable("fastembed")
                    self._model = TextEmbedding(self.name, cache_dir=cache)
                finally:
                    logger.enable("fastembed")
            except Exception as error:
                raise EmbeddingError(
                    f"could not load embedding model '{self.name}': {error}"
                ) from error
        return self._model

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return [[float(x) for x in vector] for vector in self._load().passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self._load().query_embed([text])))
        return [float(x) for x in vector]


class OpenRouterEmbedder:
    """Remote embeddings using only the dedicated embedding key; no local fallback.

    See docs/decisions/0001-openrouter-embeddings.md for the credential boundary.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        *,
        http_client: httpx2.Client | None = None,
    ) -> None:
        self.name = model
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            max_retries=0,
            http_client=http_client,
        )

    def close(self) -> None:
        self._client.close()

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(
                model=self.name, input=list(texts), encoding_format="float"
            )
        except openai.APIStatusError as error:
            # Provider response bodies can echo submitted text. Keep them out of UI/logs;
            # an out-of-credits reply gets a remedy instead of its raw wording.
            if error.status_code == 402:
                raise EmbeddingError(
                    "the OpenRouter embedding key has no balance (HTTP 402): "
                    f"add credits at {OPENROUTER_CREDITS_URL}"
                ) from None
            raise EmbeddingError(
                f"OpenRouter embedding request failed with HTTP {error.status_code}"
            ) from None
        except openai.APIConnectionError:
            raise EmbeddingError("could not reach OpenRouter embeddings") from None
        rows = sorted(response.data, key=lambda row: row.index)
        if [row.index for row in rows] != list(range(len(texts))):
            raise EmbeddingError("OpenRouter returned missing or duplicate embedding indices")
        vectors = [row.embedding for row in rows]
        dimensions = {len(vector) for vector in vectors}
        if (
            len(dimensions) != 1
            or 0 in dimensions
            or any(not math.isfinite(x) for vector in vectors for x in vector)
        ):
            raise EmbeddingError("OpenRouter returned invalid embedding vectors")
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_passages([text])[0]


def make_embedder(home: Path) -> Embedder:
    """Select the provider explicitly; remote failures never load a local model."""
    provider = (os.environ.get("CHATLORE_EMBEDDING_PROVIDER") or "fastembed").strip().lower()
    if provider == "openrouter":
        key = os.environ.get("CHATLORE_EMBEDDING_API_KEY")
        if not key:
            raise EmbeddingError("set CHATLORE_EMBEDDING_API_KEY for OpenRouter embeddings")
        model = os.environ.get(MODEL_ENV) or "openai/text-embedding-3-small"
        return OpenRouterEmbedder(model, key)
    if provider != "fastembed":
        raise EmbeddingError("CHATLORE_EMBEDDING_PROVIDER must be openrouter or fastembed")
    model = os.environ.get(MODEL_ENV) or DEFAULT_MODEL
    return FastEmbedEmbedder(model, cache_dir=home / "cache" / "models")


def normalise(vector: Sequence[float]) -> list[float]:
    """Scale a vector to unit length so L2 distance ranks like cosine similarity."""
    length = math.sqrt(sum(x * x for x in vector))
    if length == 0.0:
        return [float(x) for x in vector]
    return [float(x) / length for x in vector]


def text_hash(text: str) -> str:
    """Hash used as the cache key for a piece of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """Vectors on disk, keyed by model name and text hash."""

    def __init__(self, path: Path | str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path))
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "model TEXT NOT NULL, text_hash TEXT NOT NULL, vector BLOB NOT NULL, "
            "PRIMARY KEY (model, text_hash))"
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def get_many(self, model: str, hashes: Sequence[str]) -> dict[str, list[float]]:
        found: dict[str, list[float]] = {}
        for digest in hashes:
            row = self._connection.execute(
                "SELECT vector FROM embeddings WHERE model = ? AND text_hash = ?",
                (model, digest),
            ).fetchone()
            if row is not None:
                values = array("f")
                values.frombytes(row[0])
                found[digest] = list(values)
        return found

    def put_many(self, model: str, vectors: Mapping[str, Sequence[float]]) -> None:
        self._connection.executemany(
            "INSERT OR REPLACE INTO embeddings (model, text_hash, vector) VALUES (?, ?, ?)",
            [(model, digest, array("f", vector).tobytes()) for digest, vector in vectors.items()],
        )
        self._connection.commit()
