"""Legal RAG pipeline for `data/luat_lao_dong.md`.

The implementation is intentionally compact:
- split the markdown corpus by headings and paragraphs
- embed chunks with OpenAI when an API key is available
- retrieve by cosine similarity
- answer with OpenAI, or fall back to an extractive answer locally
"""

from __future__ import annotations

import hashlib
import json
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from openai import OpenAI

from config import (
    CACHE_DIR,
    CORPUS_PATH,
    OPENAI_API_KEY,
    OPENAI_CHAT_MODEL,
    OPENAI_EMBEDDING_MODEL,
    RAG_CHUNK_SIZE,
    RAG_MAX_OUTPUT_TOKENS,
    RAG_MIN_SCORE,
    RAG_TOP_K,
)


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
ARTICLE_RE = re.compile(r"(Điều\s+\d+[A-Z]?)", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹĐđ_]+", re.UNICODE)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass
class RAGResult:
    question: str
    answer: str
    sources: list[dict]
    retrieved: list[RetrievedChunk]


def _require_openai_key() -> None:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Create a .env file before running the pipeline."
        )


def _normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _heading_label(path: list[str]) -> str:
    return " / ".join(part for part in path if part).strip()


def _extract_article_label(heading_path: list[str]) -> str:
    for title in reversed(heading_path):
        match = ARTICLE_RE.search(title)
        if match:
            return match.group(1)
    return ""


def _split_markdown_sections(text: str) -> list[dict]:
    lines = text.splitlines()
    sections: list[dict] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    current_meta = {"heading_path": [], "heading_level": 0, "section_title": ""}

    def flush() -> None:
        block = "\n".join(current_lines).strip()
        if not block:
            return
        sections.append(
            {
                "text": block,
                "metadata": {
                    "heading_path": current_meta["heading_path"].copy(),
                    "heading_level": current_meta["heading_level"],
                    "section_title": current_meta["section_title"],
                },
            }
        )

    for line in lines:
        match = HEADING_RE.match(line.strip())
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack[:] = heading_stack[: max(level - 1, 0)]
            heading_stack.append(title)
            current_lines = [line]
            current_meta = {
                "heading_path": heading_stack.copy(),
                "heading_level": level,
                "section_title": title,
            }
            continue
        current_lines.append(line)

    flush()
    return sections


def _hard_wrap(text: str, max_chars: int) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + max_chars)
        if end < len(normalized):
            split_at = normalized.rfind(" ", start, end)
            if split_at <= start + max_chars // 3:
                split_at = end
            end = split_at if split_at > start else end
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end
        while start < len(normalized) and normalized[start].isspace():
            start += 1
    return chunks


def _split_section_text(text: str, max_chars: int) -> list[str]:
    if not text.strip():
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return _hard_wrap(text, max_chars)

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        normalized = _normalize_text(paragraph)
        if len(normalized) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_hard_wrap(normalized, max_chars))
            continue

        candidate = normalized if not current else f"{current}\n\n{normalized}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = normalized

    if current.strip():
        chunks.append(current.strip())
    return chunks


def _chunk_sections(sections: list[dict], chunk_size: int, source_name: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in sections:
        text = section["text"]
        metadata = section["metadata"]
        heading_path = metadata.get("heading_path", [])
        article = _extract_article_label(heading_path)
        section_label = _heading_label(heading_path)

        for idx, piece in enumerate(_split_section_text(text, chunk_size)):
            chunks.append(
                Chunk(
                    text=piece,
                    metadata={
                        "source": source_name,
                        "article": article,
                        "section_title": section_label,
                        "heading_path": heading_path,
                        "heading_level": metadata.get("heading_level", 0),
                        "chunk_index": idx,
                        "char_length": len(piece),
                    },
                )
            )
    return chunks


def build_chunks_from_corpus(
    path: Path = CORPUS_PATH,
    chunk_size: int = RAG_CHUNK_SIZE,
) -> list[Chunk]:
    text = _read_text(path)
    sections = _split_markdown_sections(text)
    return _chunk_sections(sections, chunk_size=chunk_size, source_name=path.name)


class OpenAIEmbedder:
    def __init__(self, model: str = OPENAI_EMBEDDING_MODEL):
        _require_openai_key()
        self.model = model
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def embed_texts(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            ordered = [None] * len(batch)
            for item in response.data:
                ordered[item.index] = item.embedding
            vectors.extend(ordered)  # type: ignore[arg-type]
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=[query])
        return np.asarray(response.data[0].embedding, dtype=np.float32)


class LocalHashEmbedder:
    """Deterministic local fallback for retrieval when no API key is present."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _vectorize(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        for token in TOKEN_RE.findall(text.lower()):
            bucket = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16) % self.dim
            vector[bucket] += 1.0
        norm = float(np.linalg.norm(vector))
        if norm:
            vector /= norm
        return vector

    def embed_texts(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        return np.asarray([self._vectorize(text) for text in texts], dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        return self._vectorize(query)


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", normalized) if part.strip()]


def _extractive_answer_from_context(retrieved: list[RetrievedChunk]) -> str:
    if not retrieved:
        return "Không tìm thấy thông tin trong tài liệu."
    sentences = _split_sentences(retrieved[0].chunk.text)
    if sentences:
        return " ".join(sentences[:2])
    snippet = _normalize_text(retrieved[0].chunk.text)
    return snippet[:500] if snippet else "Không tìm thấy thông tin trong tài liệu."


@dataclass
class VectorIndex:
    chunks: list[Chunk]
    vectors: np.ndarray
    source_fingerprint: str
    corpus_path: str
    embedding_model: str

    def search(self, query_vector: np.ndarray, top_k: int = RAG_TOP_K) -> list[RetrievedChunk]:
        if self.vectors.size == 0:
            return []
        q = query_vector.astype(np.float32)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0:
            return []
        q = q / q_norm
        scores = self.vectors @ q
        order = np.argsort(-scores)[: max(1, top_k)]
        return [RetrievedChunk(chunk=self.chunks[idx], score=float(scores[idx])) for idx in order]


def _fingerprint(path: Path, chunk_size: int, embedding_model: str) -> str:
    stat = path.stat()
    payload = f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{chunk_size}|{embedding_model}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_paths() -> tuple[Path, Path]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "rag_index.pkl", CACHE_DIR / "rag_index_meta.json"


def build_or_load_index(
    corpus_path: Path = CORPUS_PATH,
    chunk_size: int = RAG_CHUNK_SIZE,
    force_rebuild: bool = False,
) -> VectorIndex:
    index_path, meta_path = _cache_paths()
    embedding_model = OPENAI_EMBEDDING_MODEL if OPENAI_API_KEY else "local-hash-v1"
    fingerprint = _fingerprint(corpus_path, chunk_size, embedding_model)

    if not force_rebuild and index_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("fingerprint") == fingerprint:
                with index_path.open("rb") as handle:
                    cached = pickle.load(handle)
                if isinstance(cached, VectorIndex):
                    return cached
        except Exception:
            pass

    chunks = build_chunks_from_corpus(path=corpus_path, chunk_size=chunk_size)
    if not chunks:
        raise RuntimeError(f"No chunks were produced from {corpus_path}")

    embedder: OpenAIEmbedder | LocalHashEmbedder
    embedder = OpenAIEmbedder() if OPENAI_API_KEY else LocalHashEmbedder()
    try:
        vectors = _normalize_matrix(embedder.embed_texts([chunk.text for chunk in chunks]))
    except Exception:
        embedder = LocalHashEmbedder()
        vectors = _normalize_matrix(embedder.embed_texts([chunk.text for chunk in chunks]))
        embedding_model = "local-hash-v1"
        fingerprint = _fingerprint(corpus_path, chunk_size, embedding_model)

    index = VectorIndex(
        chunks=chunks,
        vectors=vectors,
        source_fingerprint=fingerprint,
        corpus_path=str(corpus_path),
        embedding_model=embedding_model,
    )

    try:
        with index_path.open("wb") as handle:
            pickle.dump(index, handle)
        meta_path.write_text(
            json.dumps(
                {
                    "fingerprint": fingerprint,
                    "corpus_path": str(corpus_path),
                    "embedding_model": embedding_model,
                    "chunk_size": chunk_size,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    return index


class RAGPipeline:
    def __init__(
        self,
        corpus_path: Path = CORPUS_PATH,
        chat_model: str = OPENAI_CHAT_MODEL,
        embedding_model: str = OPENAI_EMBEDDING_MODEL,
        top_k: int = RAG_TOP_K,
        min_score: float = RAG_MIN_SCORE,
        chunk_size: int = RAG_CHUNK_SIZE,
    ):
        self.corpus_path = corpus_path
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.min_score = min_score
        self.chunk_size = chunk_size
        self.client: OpenAI | None = None
        self.index: VectorIndex | None = None
        self._embedder: OpenAIEmbedder | LocalHashEmbedder | None = None

    @classmethod
    def from_default(cls) -> "RAGPipeline":
        return cls()

    def _get_client(self) -> OpenAI:
        _require_openai_key()
        if self.client is None:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        return self.client

    def _get_embedder(self) -> OpenAIEmbedder | LocalHashEmbedder:
        if self._embedder is None:
            self._embedder = (
                OpenAIEmbedder(model=self.embedding_model)
                if OPENAI_API_KEY
                else LocalHashEmbedder()
            )
        return self._embedder

    def build(self, force_rebuild: bool = False) -> VectorIndex:
        if self.index is None or force_rebuild:
            self.index = build_or_load_index(
                corpus_path=self.corpus_path,
                chunk_size=self.chunk_size,
                force_rebuild=force_rebuild,
            )
        return self.index

    def retrieve(self, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
        index = self.build()
        embedder = self._get_embedder()
        try:
            qvec = embedder.embed_query(question)
        except Exception:
            self._embedder = LocalHashEmbedder()
            if index.embedding_model != "local-hash-v1":
                self.index = build_or_load_index(
                    corpus_path=self.corpus_path,
                    chunk_size=self.chunk_size,
                    force_rebuild=True,
                )
                index = self.index
            qvec = self._embedder.embed_query(question)
        return index.search(qvec, top_k=top_k or self.top_k)

    def _format_context(self, retrieved: list[RetrievedChunk]) -> str:
        blocks: list[str] = []
        for pos, item in enumerate(retrieved, start=1):
            metadata = item.chunk.metadata
            label_parts: list[str] = []
            if metadata.get("article"):
                label_parts.append(metadata["article"])
            if metadata.get("section_title") and metadata.get("section_title") != metadata.get("article"):
                label_parts.append(metadata["section_title"])
            label = " - ".join(label_parts) if label_parts else metadata.get("source", "corpus")
            blocks.append(f"[{pos}] {label}\nScore: {item.score:.4f}\n{item.chunk.text}")
        return "\n\n".join(blocks)

    def answer(self, question: str) -> RAGResult:
        retrieved = self.retrieve(question)
        sources = [
            {
                "score": round(item.score, 4),
                "source": item.chunk.metadata.get("source", ""),
                "article": item.chunk.metadata.get("article", ""),
                "section_title": item.chunk.metadata.get("section_title", ""),
            }
            for item in retrieved
        ]

        if not retrieved or retrieved[0].score < self.min_score:
            return RAGResult(
                question=question,
                answer="Không tìm thấy thông tin đủ tin cậy trong tài liệu.",
                sources=sources,
                retrieved=retrieved,
            )

        if not OPENAI_API_KEY:
            return RAGResult(
                question=question,
                answer=_extractive_answer_from_context(retrieved),
                sources=sources,
                retrieved=retrieved,
            )

        context = self._format_context(retrieved)
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self.chat_model,
                temperature=0.0,
                max_tokens=RAG_MAX_OUTPUT_TOKENS,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là trợ lý hỏi đáp về Bộ luật Lao động Việt Nam. "
                            "Chỉ trả lời dựa trên CONTEXT được cung cấp. "
                            "Nếu không đủ căn cứ, hãy trả lời đúng câu: "
                            "\"Không tìm thấy thông tin trong tài liệu.\" "
                            "Trả lời ngắn gọn, chính xác, bằng tiếng Việt. "
                            "Nếu có thể, nêu rõ điều/khoản liên quan."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}",
                    },
                ],
            )
            answer = (response.choices[0].message.content or "").strip()
        except Exception:
            answer = _extractive_answer_from_context(retrieved)

        if not answer:
            answer = "Không tìm thấy thông tin trong tài liệu."

        return RAGResult(question=question, answer=answer, sources=sources, retrieved=retrieved)


def pretty_print_result(result: RAGResult) -> str:
    lines = [
        f"Câu hỏi: {result.question}",
        f"Trả lời: {result.answer}",
        "",
        "Nguồn truy hồi:",
    ]
    for idx, source in enumerate(result.sources, start=1):
        title = source.get("article") or source.get("section_title") or source.get("source") or "corpus"
        lines.append(f"  {idx}. {title} | score={source.get('score', 0):.4f}")
    return "\n".join(lines)
