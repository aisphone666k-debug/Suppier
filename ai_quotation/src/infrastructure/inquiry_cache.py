from dataclasses import dataclass
import hashlib
import time
from typing import Optional


@dataclass
class _InquiryPayload:
    answer: str
    expires_at: float
    citations: tuple = ()


class MemoryInquiryCache:
    """High-speed key-value cache for natural language RAG inquiry answers."""

    def __init__(self, ttl_seconds: float = 1800.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, _InquiryPayload] = {}
        self._hits: int = 0
        self._misses: int = 0

    def _normalize_key(self, query: str, user_role: str) -> str:
        clean_query = " ".join(query.strip().lower().split())
        clean_role = user_role.strip().upper()
        composite = f"{clean_role}:{clean_query}"
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()

    def get_entry(self, query: str, user_role: str = "NORMAL_USER") -> Optional[tuple[str, tuple]]:
        key = self._normalize_key(query, user_role)
        payload = self._store.get(key)
        now = time.time()
        if not payload:
            self._misses += 1
            return None

        if now > payload.expires_at:
            del self._store[key]
            self._misses += 1
            return None

        self._hits += 1
        return payload.answer, payload.citations

    def get(self, query: str, user_role: str = "NORMAL_USER") -> Optional[str]:
        entry = self.get_entry(query, user_role)
        return entry[0] if entry is not None else None

    def put(self, query: str, user_role: str, answer: str, citations: tuple = ()) -> None:
        key = self._normalize_key(query, user_role)
        expires_at = time.time() + self._ttl_seconds
        self._store[key] = _InquiryPayload(answer=answer, expires_at=expires_at, citations=citations)

    def invalidate_all(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

    def metrics(self) -> dict[str, float]:
        total = self._hits + self._misses
        ratio = (self._hits / total) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_ratio": round(ratio, 4),
        }
