import time
import pytest

from src.infrastructure.inquiry_cache import MemoryInquiryCache


def test_inquiry_cache_put_and_get():
    cache = MemoryInquiryCache(ttl_seconds=60)
    assert cache.get("What is the price of belt?", user_role="NORMAL_USER") is None

    cache.put(
        query="What is the price of belt?",
        user_role="NORMAL_USER",
        answer="The price is 1500 THB.",
    )

    cached_answer = cache.get("What is the price of belt?", user_role="NORMAL_USER")
    assert cached_answer == "The price is 1500 THB."


def test_inquiry_cache_normalizes_whitespace_and_case():
    cache = MemoryInquiryCache(ttl_seconds=60)
    cache.put(
        query="What is the price of belt?  ",
        user_role="NORMAL_USER",
        answer="1500 THB",
    )

    # Different case and surrounding whitespace should hit the same cache key
    assert cache.get("  what IS the price of BELT? ", user_role="NORMAL_USER") == "1500 THB"


def test_inquiry_cache_role_isolation():
    cache = MemoryInquiryCache(ttl_seconds=60)
    cache.put(query="List items", user_role="NORMAL_USER", answer="Normal view")
    cache.put(query="List items", user_role="PH_USER", answer="PH view")

    assert cache.get("List items", user_role="NORMAL_USER") == "Normal view"
    assert cache.get("List items", user_role="PH_USER") == "PH view"


def test_inquiry_cache_respects_ttl():
    # 0.1 second TTL
    cache = MemoryInquiryCache(ttl_seconds=0.05)
    cache.put(query="Fast query", user_role="NORMAL_USER", answer="Temporary answer")
    assert cache.get("Fast query", user_role="NORMAL_USER") == "Temporary answer"

    time.sleep(0.06)
    assert cache.get("Fast query", user_role="NORMAL_USER") is None


def test_inquiry_cache_tracks_hit_and_miss_metrics():
    cache = MemoryInquiryCache(ttl_seconds=60)
    # Miss 1
    cache.get("Query A", "NORMAL_USER")
    # Miss 2
    cache.get("Query B", "NORMAL_USER")

    cache.put("Query A", "NORMAL_USER", "Answer A")

    # Hit 1
    cache.get("Query A", "NORMAL_USER")
    # Hit 2
    cache.get("Query A", "NORMAL_USER")

    stats = cache.metrics()
    assert stats["hits"] == 2
    assert stats["misses"] == 2
    assert stats["hit_ratio"] == 0.5


def test_inquiry_cache_invalidate_all():
    cache = MemoryInquiryCache(ttl_seconds=60)
    cache.put("Q1", "NORMAL_USER", "A1")
    cache.put("Q2", "NORMAL_USER", "A2")
    assert cache.size() == 2

    cache.invalidate_all()
    assert cache.size() == 0
    assert cache.get("Q1", "NORMAL_USER") is None
