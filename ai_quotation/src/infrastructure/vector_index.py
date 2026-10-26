from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
import numpy as np

from src.domain.quotation import QuotationId


@dataclass(frozen=True)
class VectorSearchResult:
    quotation_id: QuotationId
    score: float
    matched_chunk: Optional[str] = None


@dataclass
class VectorChunk:
    chunk_id: str
    quotation_id: QuotationId
    vector: np.ndarray
    label: str = ""


class MemoryVectorIndex:
    """In-memory hybrid vector index with cosine similarity, token keyword matching,

    and granular line-item chunk indexing.
    """

    def __init__(self) -> None:
        self._vectors: Dict[QuotationId, np.ndarray] = {}
        self._chunks: Dict[str, VectorChunk] = {}
        self._token_index: Dict[str, Set[QuotationId]] = {}

    def __len__(self) -> int:
        return len(self._vectors)

    def add(self, quotation_id: QuotationId, vector: np.ndarray, keywords: list[str]) -> None:
        # Normalize vector for cosine distance computation
        norm = np.linalg.norm(vector)
        if norm > 0:
            norm_vector = vector / norm
        else:
            norm_vector = vector
        self._vectors[quotation_id] = norm_vector.astype(np.float32)

        from src.domain.multilingual_lexicon import MultilingualLexicon
        lexicon = MultilingualLexicon()

        # Inverted token index with multilingual tokenization and cross-lingual expansion
        for kw in keywords:
            if not kw:
                continue
            # Extract unicode words (supports English, Thai, Japanese)
            words = lexicon.extract_unicode_tokens(kw)
            for word in words:
                synonyms = lexicon.expand_terms(word)
                for syn in synonyms:
                    if syn not in self._token_index:
                        self._token_index[syn] = set()
                    self._token_index[syn].add(quotation_id)

            # Whole phrase
            token = kw.strip().lower()
            if token not in self._token_index:
                self._token_index[token] = set()
            self._token_index[token].add(quotation_id)
            for syn in lexicon.expand_terms(token):
                if syn not in self._token_index:
                    self._token_index[syn] = set()
                self._token_index[syn].add(quotation_id)

    def add_chunk(self, chunk_id: str, quotation_id: QuotationId, vector: np.ndarray, label: str = "") -> None:
        """Adds a granular line-item or text-chunk vector."""
        norm = np.linalg.norm(vector)
        if norm > 0:
            norm_vector = vector / norm
        else:
            norm_vector = vector
        self._chunks[chunk_id] = VectorChunk(
            chunk_id=chunk_id,
            quotation_id=quotation_id,
            vector=norm_vector.astype(np.float32),
            label=label,
        )

    def remove(self, quotation_id: QuotationId) -> None:
        if quotation_id in self._vectors:
            del self._vectors[quotation_id]
        # Remove associated chunks
        chunks_to_remove = [
            cid for cid, ch in self._chunks.items() if ch.quotation_id == quotation_id
        ]
        for cid in chunks_to_remove:
            del self._chunks[cid]
        for token_set in self._token_index.values():
            token_set.discard(quotation_id)

    def search(self, query_vector: np.ndarray, limit: int = 25) -> list[VectorSearchResult]:
        if not self._vectors and not self._chunks:
            return []

        norm = np.linalg.norm(query_vector)
        if norm > 0:
            q_norm = query_vector / norm
        else:
            q_norm = query_vector

        # Map quotation_id -> highest similarity score across doc-level & chunk-level
        score_map: Dict[QuotationId, float] = {}
        matched_chunk_map: Dict[QuotationId, str] = {}

        # 1. Document-level vectors
        for qid, vec in self._vectors.items():
            sim = float(np.dot(q_norm, vec))
            score = max(0.0, min(1.0, sim))
            score_map[qid] = score
            matched_chunk_map[qid] = "document_composite"

        # 2. Granular Line-item chunk vectors
        for cid, chunk in self._chunks.items():
            sim = float(np.dot(q_norm, chunk.vector))
            score = max(0.0, min(1.0, sim))
            if score > score_map.get(chunk.quotation_id, 0.0):
                score_map[chunk.quotation_id] = score
                matched_chunk_map[chunk.quotation_id] = chunk.label or cid

        results = [
            VectorSearchResult(
                quotation_id=qid,
                score=round(score, 4),
                matched_chunk=matched_chunk_map.get(qid),
            )
            for qid, score in score_map.items()
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_by_tokens(self, tokens: list[str]) -> list[VectorSearchResult]:
        """Matches exact token tokens and cross-lingual synonyms (English, Thai, Japanese) with high confidence."""
        from src.domain.multilingual_lexicon import MultilingualLexicon
        lexicon = MultilingualLexicon()

        expanded_tokens: set[str] = set()
        for t in tokens:
            expanded_tokens.update(lexicon.expand_terms(t))
            for sub in lexicon.extract_unicode_tokens(t):
                expanded_tokens.update(lexicon.expand_terms(sub))

        match_counts: dict[QuotationId, int] = {}
        for t in expanded_tokens:
            normalized_token = t.strip().lower()
            if normalized_token in self._token_index:
                for qid in self._token_index[normalized_token]:
                    match_counts[qid] = match_counts.get(qid, 0) + 1

        results = [
            VectorSearchResult(quotation_id=qid, score=min(0.99, 0.95 + 0.02 * (count - 1)))
            for qid, count in match_counts.items()
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results
