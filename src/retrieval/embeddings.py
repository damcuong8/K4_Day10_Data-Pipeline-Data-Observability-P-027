from __future__ import annotations

from functools import lru_cache
import math

from langchain_core.embeddings import Embeddings

# Gemini embed API gioi han so text moi request; chia batch de tranh loi 400.
GEMINI_BATCH_SIZE = 50
# OpenAI cho phep nhieu text moi request hon.
OPENAI_BATCH_SIZE = 100


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


class GeminiEmbeddings(Embeddings):
    """Gemini embedding qua API. Dung task_type rieng cho document va query."""

    def __init__(self, model_name: str, api_key: str | None, output_dimensionality: int = 768):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required when EMBEDDING_PROVIDER=gemini.")

        common = {
            "model": model_name,
            "google_api_key": api_key,
            "output_dimensionality": output_dimensionality,
        }
        self._document_client = GoogleGenerativeAIEmbeddings(task_type="retrieval_document", **common)
        self._query_client = GoogleGenerativeAIEmbeddings(task_type="retrieval_query", **common)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), GEMINI_BATCH_SIZE):
            batch = texts[start : start + GEMINI_BATCH_SIZE]
            vectors.extend(self._document_client.embed_documents(batch))
        return [_normalize(vector) for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return _normalize(self._query_client.embed_query(text))


class OpenAIEmbeddingsBackend(Embeddings):
    """OpenAI embedding qua API. text-embedding-3-* ho tro rut gon so chieu."""

    def __init__(self, model_name: str, api_key: str | None, dimensions: int = 768):
        from langchain_openai import OpenAIEmbeddings

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")

        kwargs = {"model": model_name, "api_key": api_key, "chunk_size": OPENAI_BATCH_SIZE}
        # Chi model v3 moi nhan tham so dimensions; ada-002 co dinh 1536 chieu.
        if model_name.startswith("text-embedding-3"):
            kwargs["dimensions"] = dimensions
        self._client = OpenAIEmbeddings(**kwargs)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(vector) for vector in self._client.embed_documents(texts)]

    def embed_query(self, text: str) -> list[float]:
        return _normalize(self._client.embed_query(text))


def build_embeddings(settings) -> Embeddings:
    """Chon embedding backend theo settings.embedding_provider."""
    provider = settings.embedding_provider.strip().lower()
    if provider == "gemini":
        return GeminiEmbeddings(
            model_name=settings.embedding_model,
            api_key=settings.google_api_key,
            output_dimensionality=settings.embedding_dimensions,
        )
    if provider == "openai":
        return OpenAIEmbeddingsBackend(
            model_name=settings.embedding_model,
            api_key=settings.openai_api_key,
            dimensions=settings.embedding_dimensions,
        )
    if provider in {"minilm", "local", "sentence-transformers"}:
        return MiniLMEmbeddings(settings.embedding_model)
    raise RuntimeError(
        f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}. "
        "Expected one of: gemini, openai, minilm."
    )
