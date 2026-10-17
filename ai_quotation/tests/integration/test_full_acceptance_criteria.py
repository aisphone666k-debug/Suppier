from datetime import date, timedelta
import os
import sqlite3
import pytest

from src.domain.quotation import QuotationId, QuotationStatus
from src.domain.manual_quotation_request import RequestStatus, RequestUrgency
from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.infrastructure.search_cache import MemorySearchCache
from src.infrastructure.vector_index import MemoryVectorIndex
from src.infrastructure.embedding_engine import FastEmbedEngine
from src.application.quotation_service import QuotationApplicationService
from src.interfaces.web_app import seed_existing_quotations


@pytest.fixture(scope="module")
def seeded_service():
    """Builds a real service instance seeded with the actual PDF quotations in quoatation/."""
    conn = sqlite3.connect(":memory:")
    q_repo = SqliteQuotationRepository(conn)
    q_repo.initialize_schema()

    m_repo = SqliteManualRequestRepository(conn)
    m_repo.initialize_schema()

    cache = MemorySearchCache(ttl_seconds=300)
    v_index = MemoryVectorIndex()
    engine = FastEmbedEngine()

    svc = QuotationApplicationService(
        quotation_repository=q_repo,
        manual_request_repository=m_repo,
        search_cache=cache,
        vector_index=v_index,
        embedding_engine=engine,
    )

    seeded_count = seed_existing_quotations(svc, sample_dir="quoatation")
    assert seeded_count > 0, f"Expected at least 1 seeded quotation from quoatation/, got {seeded_count}"
    return svc


def test_ac01_semantic_search_with_real_pdf_data(seeded_service):
    """AC-01: Semantic Match with High Confidence using actual PDF content."""
    today = date.today()

    # Search for Bando V-Belt
    results = seeded_service.search(
        query="Bando V-Belt transmission power",
        user_role="NORMAL_USER",
        reference_date=today,
    )
    assert len(results) > 0
    top = results[0]
    assert "bando" in top.quotation.vendor_name.lower() or "bando" in top.quotation.quotation_number.lower()
    assert top.confidence.value >= 0.40
    assert top.can_receive is True


def test_ac02_dual_layer_cache_and_invalidation(seeded_service):
    """AC-02: Key-Value Caching & Invalidation."""
    today = date.today()
    query = "Minebea Thai project"

    # 1. Miss & populate
    res1 = seeded_service.search(query, user_role="NORMAL_USER", reference_date=today)
    assert len(res1) > 0

    # 2. Cache Hit verified
    cached = seeded_service.search_cache.get(query)
    assert cached is not None
    assert len(cached) > 0

    # 3. New quotation registered -> Cache flushed
    seeded_service.register_quotation(
        quotation_number="TEST-NEW-FLUSH",
        vendor_name="Cache Flush Vendor",
        issue_date=today,
        expiration_date=today + timedelta(days=90),
        items=[{"item_number": 1, "description": "Flush Item", "quantity": 1.0, "unit": "Pcs", "unit_price": 100.0}],
        pdf_path="quoatation/25-334.pdf",
        pdf_sha256="fake_sha",
        user_role="PH_USER",
    )
    assert seeded_service.search_cache.get(query) is None


def test_ac04_normal_user_receive_quotation(seeded_service):
    """AC-04: Normal User Quotation Acknowledgment ('Receive')."""
    today = date.today()
    all_q = seeded_service.list_all_quotations()
    target_q = next(q for q in all_q if not q.validity_period.is_expired(today))

    ack = seeded_service.acknowledge_quotation(
        quotation_id=target_q.quotation_id,
        user_id="engineer_007",
        reference_date=today,
    )
    assert ack.quotation_id == target_q.quotation_id
    assert ack.user_id == "engineer_007"

    # Verify audit log in repository
    audit = seeded_service.quotation_repository.get_acknowledgments(target_q.quotation_id)
    assert len(audit) >= 1
    assert any(a.user_id == "engineer_007" for a in audit)


def test_ac05_expiration_handling_and_ph_renewal(seeded_service):
    """AC-05: Expiration Management by Date & PH Renewal."""
    today = date.today()
    past_date = today - timedelta(days=10)

    # Register an expired quotation
    expired_q = seeded_service.register_quotation(
        quotation_number="EXPIRED-AC05",
        vendor_name="Outdated Vendor Corp",
        issue_date=past_date - timedelta(days=60),
        expiration_date=past_date,
        items=[{"item_number": 1, "description": "Obsolete Part XYZ", "quantity": 1.0, "unit": "Pcs", "unit_price": 500.0}],
        pdf_path="quoatation/416359.pdf",
        pdf_sha256="sha_obsolete",
        user_role="PH_USER",
    )

    # Normal user cannot find it in search
    normal_res = seeded_service.search("Obsolete Part XYZ", user_role="NORMAL_USER", reference_date=today)
    assert not any(r.quotation.quotation_id == expired_q.quotation_id for r in normal_res)

    # Appears in PH expired list
    expired_list = seeded_service.list_expired_quotations(reference_date=today)
    assert any(eq.quotation_id == expired_q.quotation_id for eq in expired_list)

    # PH Renews it with future date
    future_date = today + timedelta(days=180)
    renewed = seeded_service.renew_quotation(
        quotation_id=expired_q.quotation_id,
        new_expiration_date=future_date,
        user_role="PH_USER",
        reference_date=today,
        remarks="Vendor contract renewed for 6 months",
    )
    assert renewed.status == QuotationStatus.ACTIVE

    # Now Normal user CAN find and receive it
    normal_res_after = seeded_service.search("Obsolete Part XYZ", user_role="NORMAL_USER", reference_date=today)
    assert any(r.quotation.quotation_id == expired_q.quotation_id for r in normal_res_after)


def test_ac06_manual_quotation_request_lifecycle(seeded_service):
    """AC-06: Manual Quotation Request Workflow."""
    # 1. Normal User submits demand
    req = seeded_service.submit_manual_request(
        requester_user_id="user_mike",
        department="Assembly Line A",
        item_description="Special Hardened Carbide End Mill 12mm",
        part_number="EM-12-CARBIDE",
        target_quantity=10.0,
        target_unit="Pcs",
        needed_by_date=date.today() + timedelta(days=14),
        urgency=RequestUrgency.CRITICAL,
    )
    assert req.status == RequestStatus.SUBMITTED

    # 2. PH user lists and fulfills demand
    pending = seeded_service.list_pending_manual_requests()
    assert any(p.ticket_id == req.ticket_id for p in pending)

    all_q = seeded_service.list_all_quotations()
    target_q = all_q[0]

    fulfilled = seeded_service.fulfill_manual_request(
        ticket_id=req.ticket_id,
        quotation_id=target_q.quotation_id,
        ph_user_id="ph_officer_sarah",
        user_role="PH_USER",
    )
    assert fulfilled.status == RequestStatus.FULFILLED
    assert fulfilled.fulfilled_quotation_id == target_q.quotation_id
