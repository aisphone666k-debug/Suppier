from datetime import date
import sqlite3
import pytest

from src.domain.quotation import Quotation, QuotationId, QuotationStatus, QuotationItem, QuotationExpiredException
from src.domain.validity_period import ValidityPeriod
from src.domain.manual_quotation_request import RequestStatus, RequestUrgency
from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.infrastructure.search_cache import MemorySearchCache
from src.infrastructure.vector_index import MemoryVectorIndex
from src.infrastructure.embedding_engine import FastEmbedEngine
from src.application.quotation_service import QuotationApplicationService


@pytest.fixture
def service():
    conn = sqlite3.connect(":memory:")
    quotation_repo = SqliteQuotationRepository(conn)
    quotation_repo.initialize_schema()

    manual_repo = SqliteManualRequestRepository(conn)
    manual_repo.initialize_schema()

    cache = MemorySearchCache(ttl_seconds=300)
    vector_index = MemoryVectorIndex()
    embedding_engine = FastEmbedEngine()

    return QuotationApplicationService(
        quotation_repository=quotation_repo,
        manual_request_repository=manual_repo,
        search_cache=cache,
        vector_index=vector_index,
        embedding_engine=embedding_engine,
    )


def test_register_and_search_quotation(service):
    today = date(2026, 9, 25)

    # 1. Register a quotation
    q = service.register_quotation(
        quotation_number="137836",
        vendor_name="Bando Chemical Industries Ltd.",
        issue_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "5V-1400",
                "description": "Power Ace Industrial V-Belt",
                "quantity": 10.0,
                "unit": "Pcs",
                "unit_price": 450.0,
            }
        ],
        pdf_path="quoatation/QT NO. 137836.pdf",
        pdf_sha256="fake_sha256",
        user_role="PH_USER",
    )

    assert q.status == QuotationStatus.ACTIVE

    # 2. Search for related semantic phrase
    results = service.search(
        query="industrial rubber transmission belt",
        user_role="NORMAL_USER",
        reference_date=today,
    )

    assert len(results) >= 1
    top_match = results[0]
    assert top_match.quotation.quotation_number == "137836"
    assert top_match.confidence.value > 0.40
    assert top_match.can_receive is True


def test_search_cache_hit_and_invalidation(service):
    today = date(2026, 9, 25)
    service.register_quotation(
        quotation_number="137836",
        vendor_name="Bando Chemical Industries Ltd.",
        issue_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "5V-1400",
                "description": "V-Belt",
                "quantity": 5.0,
                "unit": "Pcs",
                "unit_price": 400.0,
            }
        ],
        pdf_path="quoatation/QT NO. 137836.pdf",
        pdf_sha256="fake_sha256",
        user_role="PH_USER",
    )

    # First search -> Cache Miss & Write
    res1 = service.search("V-Belt", user_role="NORMAL_USER", reference_date=today)
    assert len(res1) == 1

    # Second search -> Cache Hit
    assert service.search_cache.get("V-Belt") is not None

    # Registering a new quotation invalidates cache
    service.register_quotation(
        quotation_number="25-334",
        vendor_name="Siam Precision",
        issue_date=date(2026, 2, 1),
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "FLG-100",
                "description": "Precision Flange",
                "quantity": 2.0,
                "unit": "Pcs",
                "unit_price": 1200.0,
            }
        ],
        pdf_path="quoatation/25-334.pdf",
        pdf_sha256="fake_sha2",
        user_role="PH_USER",
    )

    # Cache should be purged
    assert service.search_cache.get("V-Belt") is None


def test_expired_quotation_hidden_from_normal_user(service):
    today = date(2026, 9, 25)
    # Register expired quotation
    service.register_quotation(
        quotation_number="OLD-01",
        vendor_name="Old Vendor",
        issue_date=date(2025, 1, 1),
        expiration_date=date(2026, 1, 1),
        items=[
            {
                "item_number": 1,
                "part_number": "OLD-ITEM",
                "description": "Old Expired Sensor",
                "quantity": 1.0,
                "unit": "Pcs",
                "unit_price": 100.0,
            }
        ],
        pdf_path="storage/old.pdf",
        pdf_sha256="sha_old",
        user_role="PH_USER",
    )

    # Normal user search should NOT return expired quotation
    normal_res = service.search("Old Expired Sensor", user_role="NORMAL_USER", reference_date=today)
    assert len(normal_res) == 0

    # PH user can see expired quotations in search or via list_expired
    expired_list = service.list_expired_quotations(reference_date=today)
    assert len(expired_list) == 1
    assert expired_list[0].quotation_number == "OLD-01"


def test_renewal_by_ph_user_reactivates_quotation(service):
    today = date(2026, 9, 25)
    q = service.register_quotation(
        quotation_number="OLD-02",
        vendor_name="Old Vendor",
        issue_date=date(2025, 1, 1),
        expiration_date=date(2026, 1, 1),
        items=[
            {
                "item_number": 1,
                "part_number": "OLD-PART",
                "description": "Outdated Bearing",
                "quantity": 1.0,
                "unit": "Pcs",
                "unit_price": 50.0,
            }
        ],
        pdf_path="storage/old.pdf",
        pdf_sha256="sha_old",
        user_role="PH_USER",
    )

    # Non-PH cannot renew
    with pytest.raises(PermissionError):
        service.renew_quotation(
            quotation_id=q.quotation_id,
            new_expiration_date=date(2027, 12, 31),
            user_role="NORMAL_USER",
            reference_date=today,
            remarks="Unauthorized attempt",
        )

    # PH user successfully renews
    renewed = service.renew_quotation(
        quotation_id=q.quotation_id,
        new_expiration_date=date(2027, 12, 31),
        user_role="PH_USER",
        reference_date=today,
        remarks="Vendor extended contract",
    )
    assert renewed.status == QuotationStatus.ACTIVE
    assert renewed.validity_period.expiration_date == date(2027, 12, 31)

    # Now Normal user CAN find it
    res = service.search("Outdated Bearing", user_role="NORMAL_USER", reference_date=today)
    assert len(res) == 1


def test_manual_quotation_request_flow(service):
    # 0. Register quotation to fulfill with
    service.register_quotation(
        quotation_number="NEW-01",
        vendor_name="THK Linear Motion",
        issue_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "LGR-1000",
                "description": "Custom Linear Guide Rail 1000mm",
                "quantity": 4.0,
                "unit": "Pcs",
                "unit_price": 3500.0,
            }
        ],
        pdf_path="quoatation/sample.pdf",
        pdf_sha256="dummy_sha",
        user_role="PH_USER",
    )

    # 1. Normal user submits request
    ticket = service.submit_manual_request(
        requester_user_id="user_john",
        department="Production",
        item_description="Custom Linear Guide Rail 1000mm",
        part_number="LGR-1000",
        target_quantity=4.0,
        target_unit="Pcs",
        needed_by_date=date(2026, 11, 15),
        urgency=RequestUrgency.HIGH,
    )
    assert ticket.ticket_id.startswith("REQ-")
    assert ticket.status == RequestStatus.SUBMITTED

    # 2. PH user lists pending requests
    pending = service.list_pending_manual_requests()
    assert len(pending) == 1
    assert pending[0].ticket_id == ticket.ticket_id

    # 3. PH user fulfills request
    fulfilled = service.fulfill_manual_request(
        ticket_id=ticket.ticket_id,
        quotation_id=QuotationId("QT-NEW-01"),
        ph_user_id="ph_admin",
        user_role="PH_USER",
    )
    assert fulfilled.status == RequestStatus.FULFILLED
    assert fulfilled.fulfilled_quotation_id == QuotationId("QT-NEW-01")


def test_extract_draft_from_pdf(service):
    import os
    pdf_path = os.path.join("quoatation", "26Q13131 (2).pdf")

    # Non-PH cannot extract draft
    with pytest.raises(PermissionError):
        service.extract_draft_from_pdf(pdf_path=pdf_path, user_role="NORMAL_USER")

    # PH user successfully extracts draft
    draft = service.extract_draft_from_pdf(pdf_path=pdf_path, user_role="PH_USER")
    assert draft.quotation_number == "26Q13131"
    assert "IWASE" in draft.vendor_name
    assert draft.issue_date == date(2026, 7, 31)
