from src.domain.quotation import QuotationId
from src.infrastructure.bm25_index import BM25Index


def test_bm25_index_exact_match():
    index = BM25Index()
    index.add_document(
        quotation_id=QuotationId("QT-BANDO-01"),
        quotation_number="0010584101",
        vendor_name="BANDO CHEMICAL INDUSTRIES",
        part_numbers=["A-61(S)", "5V-1400"],
        descriptions=["Bando Industrial Transmission V-Belt"],
    )
    index.add_document(
        quotation_id=QuotationId("QT-OMRON-01"),
        quotation_number="SQ-126073336",
        vendor_name="Trisak Automation",
        part_numbers=["H7CC-ASD"],
        descriptions=["COUNTER OMRON DIGITAL"],
    )

    results = index.search("BANDO")
    assert len(results) == 1
    assert results[0].quotation_id == QuotationId("QT-BANDO-01")
    assert results[0].score >= 0.80

    results_pn = index.search("H7CC-ASD")
    assert len(results_pn) == 1
    assert results_pn[0].quotation_id == QuotationId("QT-OMRON-01")


def test_bm25_index_thai_and_synonyms():
    index = BM25Index()
    index.add_document(
        quotation_id=QuotationId("QT-BELT-01"),
        quotation_number="QT-100",
        vendor_name="Vendor A",
        part_numbers=["7M 1360"],
        descriptions=["Industrial Belt 7M 1360 / สายพานโรงงาน"],
    )

    results = index.search("สายพาน")
    assert len(results) == 1
    assert results[0].quotation_id == QuotationId("QT-BELT-01")


def test_bm25_index_compact_concatenation():
    index = BM25Index()
    index.add_document(
        quotation_id=QuotationId("QT-IWASE-01"),
        quotation_number="26Q13131",
        vendor_name="IWASE Thailand",
        part_numbers=["Belt 7M 1360"],
        descriptions=["Belt 7M 1360 / Gate 3"],
    )

    # Search with concatenated string without space
    results = index.search("belt7m")
    assert len(results) == 1
    assert results[0].quotation_id == QuotationId("QT-IWASE-01")
    assert results[0].score >= 0.80

    # Search with prefix number concatenation
    results_num = index.search("7m1360")
    assert len(results_num) == 1
    assert results_num[0].quotation_id == QuotationId("QT-IWASE-01")


def test_bm25_index_unit_and_spec_ranking():
    index = BM25Index()
    # Document 1: 11M Belt
    index.add_document(
        quotation_id=QuotationId("QT-TORNOS-11M"),
        quotation_number="21221998",
        vendor_name="TORNOS S.A.",
        part_numbers=["212816"],
        descriptions=["Trapezoidal belt 11M L=1600"],
    )
    # Document 2: 7M Belt
    index.add_document(
        quotation_id=QuotationId("QT-IWASE-7M"),
        quotation_number="26Q13131",
        vendor_name="IWASE Thailand",
        part_numbers=["Belt 7M 1360"],
        descriptions=["Belt 7M 1360 / Gate 3"],
    )

    # Searching Thai "สายพาน 11 เมตร" must rank 11M #1 ahead of 7M
    results_11m = index.search("สายพาน 11 เมตร")
    assert len(results_11m) >= 2
    assert results_11m[0].quotation_id == QuotationId("QT-TORNOS-11M")
    assert results_11m[0].score > results_11m[1].score

    # Searching Thai "สายพาน 7 เมตร" must rank 7M #1 ahead of 11M
    results_7m = index.search("สายพาน 7 เมตร")
    assert len(results_7m) >= 2
    assert results_7m[0].quotation_id == QuotationId("QT-IWASE-7M")
    assert results_7m[0].score > results_7m[1].score


