import numpy as np
import pytest

from src.domain.quotation import QuotationId
from src.infrastructure.vector_index import MemoryVectorIndex, VectorSearchResult


def test_vector_index_add_and_search():
    index = MemoryVectorIndex()

    # Create dummy normalized vectors
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    v3 = np.array([0.7071, 0.7071, 0.0], dtype=np.float32)

    index.add(QuotationId("QT-1"), v1, keywords=["rubber", "belt", "5v-1400"])
    index.add(QuotationId("QT-2"), v2, keywords=["valve", "titanium"])
    index.add(QuotationId("QT-3"), v3, keywords=["rubber", "flange"])

    # Query aligned with v1
    query_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = index.search(query_vec, limit=3)

    assert len(results) == 3
    # First match is QT-1 with similarity close to 1.0
    assert results[0].quotation_id == QuotationId("QT-1")
    assert round(results[0].score, 3) == 1.0
    # Second match is QT-3 with similarity ~0.707
    assert results[1].quotation_id == QuotationId("QT-3")
    assert round(results[1].score, 3) == 0.707


def test_keyword_fallback_boosting():
    index = MemoryVectorIndex()
    v1 = np.array([0.1, 0.1, 0.1], dtype=np.float32)
    v1 /= np.linalg.norm(v1)

    index.add(QuotationId("QT-EXACT"), v1, keywords=["6204zz", "bearing"])

    # Exact token query match provides score boosting
    exact_matches = index.search_by_tokens(["6204zz"])
    assert len(exact_matches) == 1
    assert exact_matches[0].quotation_id == QuotationId("QT-EXACT")
    assert exact_matches[0].score >= 0.95


def test_vector_index_remove():
    index = MemoryVectorIndex()
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    index.add(QuotationId("QT-1"), v1, keywords=["belt"])

    assert len(index) == 1
    index.remove(QuotationId("QT-1"))
    assert len(index) == 0
