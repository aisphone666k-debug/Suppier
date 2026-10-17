from dataclasses import dataclass
import hashlib
import time
from typing import Optional

from src.domain.quotation import QuotationId


@dataclass(frozen=True)
class CacheEntry:
    quotation_id: QuotationId
    confidence: float


@dataclass
class _CachePayload:
    entries: list[CacheEntry]
    expires_at: float


class MemorySearchCache:
    """Key-Value cache for semantic and keyword search queries."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, _CachePayload] = {}

    def _normalize_and_hash(self, query: str) -> str:
        normalized = " ".join(query.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, query: str) -> Optional[list[CacheEntry]]:
        key = self._normalize_and_hash(query)
        payload = self._store.get(key)
        if not payload:
            return None
        if time.time() > payload.expires_at:
            # Expired entry
            del self._store[key]
            return None
        return payload.entries

    def put(self, query: str, entries: list[CacheEntry]) -> None:
        key = self._normalize_and_hash(query)
        expires_at = time.time() + self._ttl_seconds
        self._store[key] = _CachePayload(entries=entries, expires_at=expires_at)

    def invalidate_all(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)
