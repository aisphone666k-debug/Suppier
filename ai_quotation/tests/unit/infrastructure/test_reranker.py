from datetime import date
from src.domain.quotation import Quotation, QuotationId, QuotationStatus, QuotationItem
from src.domain.validity_period import ValidityPeriod
from src.infrastructure.reranker import HybridReranker
from src.infrastructure.vector_index import VectorSearchResult
from src.infrastructure.bm25_index import BM25SearchResult


def test_hybrid_reranker_fusion():
    reranker = HybridReranker()
    qid1 = QuotationId("QT-01")

    item1 = QuotationItem(item_number=1, description="V-Belt Transmission Bando", quantity=1.0, unit="Pcs", unit_price=500.0, part_number="5V-1400")
    q1 = Quotation(
        quotation_id=qid1,
        quotation_number="0010584101",
        vendor_name="BANDO CHEMICAL",
        validity_period=ValidityPeriod(date.today(), date(2030, 1, 1)),
        status=QuotationStatus.ACTIVE,
        items=(item1,),
        pdf_path="test.pdf",
        pdf_sha256="abc",
    )

    vr1 = VectorSearchResult(quotation_id=qid1, score=0.88)
    br1 = BM25SearchResult(quotation_id=qid1, score=0.95, matched_fields=["exact_part_number"])

    reranked = reranker.fuse_and_rerank(
        query="5V-1400",
        vector_results=[vr1],
        bm25_results=[br1],
        quotations_map={qid1: q1},
    )

    assert len(reranked) == 1
    assert reranked[0].quotation_id == qid1
    assert reranked[0].final_score >= 0.80
    assert reranked[0].retrieval_stage == "HYBRID_FUSION"
