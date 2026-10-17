from datetime import date
import sqlite3
import pytest

from src.domain.manual_quotation_request import (
    ManualQuotationRequest,
    RequestStatus,
    RequestUrgency,
)
from src.domain.quotation import QuotationId
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository


@pytest.fixture
def repo():
    conn = sqlite3.connect(":memory:")
    repo = SqliteManualRequestRepository(conn)
    repo.initialize_schema()
    return repo


def test_save_and_find_by_ticket_id(repo):
    req = ManualQuotationRequest(
        ticket_id="REQ-2026-0001",
        requester_user_id="user_alice",
        department="Engineering",
        item_description="Precision Bearings 6204ZZ",
        part_number="6204ZZ",
        target_quantity=50.0,
        target_unit="Pcs",
        needed_by_date=date(2026, 11, 30),
        urgency=RequestUrgency.HIGH,
    )
    repo.save(req)

    fetched = repo.find_by_ticket_id("REQ-2026-0001")
    assert fetched is not None
    assert fetched.ticket_id == "REQ-2026-0001"
    assert fetched.item_description == "Precision Bearings 6204ZZ"
    assert fetched.urgency == RequestUrgency.HIGH
    assert fetched.status == RequestStatus.SUBMITTED


def test_find_by_status_and_fulfill(repo):
    req = ManualQuotationRequest(
        ticket_id="REQ-2026-0002",
        requester_user_id="user_bob",
        department="Maintenance",
        item_description="Hydraulic Seal Kit",
    )
    repo.save(req)

    pending = repo.find_by_status(RequestStatus.SUBMITTED)
    assert len(pending) == 1
    assert pending[0].ticket_id == "REQ-2026-0002"

    req.fulfill(QuotationId("QT-137836"), ph_user_id="ph_admin")
    repo.save(req)

    pending_after = repo.find_by_status(RequestStatus.SUBMITTED)
    assert len(pending_after) == 0

    fulfilled = repo.find_by_status(RequestStatus.FULFILLED)
    assert len(fulfilled) == 1
    assert fulfilled[0].fulfilled_quotation_id == QuotationId("QT-137836")
