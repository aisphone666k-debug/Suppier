import time
import pytest

from src.domain.quotation import QuotationId
from src.infrastructure.search_cache import MemorySearchCache, CacheEntry


def test_cache_miss_on_empty():
    cache = MemorySearchCache(ttl_seconds=60)
    result = cache.get("High-pressure rubber hose")
    assert result is None


def test_cache_put_and_hit():
    cache = MemorySearchCache(ttl_seconds=60)
    entries = [
        CacheEntry(quotation_id=QuotationId("QT-137836"), confidence=0.92),
        CacheEntry(quotation_id=QuotationId("QT-25-334"), confidence=0.78),
    ]

    cache.put("High-pressure rubber hose", entries)
    # Query with extra spaces and mixed case should normalize to same cache key
    cached = cache.get("   high-pressure  rubber   hose ")
    assert cached is not None
    assert len(cached) == 2
    assert cached[0].quotation_id == QuotationId("QT-137836")
    assert cached[0].confidence == 0.92


def test_cache_expiration_ttl():
    cache = MemorySearchCache(ttl_seconds=1)
    entries = [CacheEntry(quotation_id=QuotationId("QT-137836"), confidence=0.95)]
    cache.put("bearing 6204", entries)

    assert cache.get("bearing 6204") is not None
    time.sleep(1.1)
    assert cache.get("bearing 6204") is None


def test_cache_invalidation():
    cache = MemorySearchCache(ttl_seconds=60)
    cache.put("bearing", [CacheEntry(quotation_id=QuotationId("QT-1"), confidence=0.8)])
    cache.put("belt", [CacheEntry(quotation_id=QuotationId("QT-2"), confidence=0.9)])

    assert cache.get("bearing") is not None
    assert cache.get("belt") is not None

    cache.invalidate_all()

    assert cache.get("bearing") is None
    assert cache.get("belt") is None
