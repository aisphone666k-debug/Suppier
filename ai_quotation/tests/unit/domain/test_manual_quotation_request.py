from datetime import date
import pytest

from src.domain.manual_quotation_request import (
    ManualQuotationRequest,
    RequestStatus,
    RequestUrgency,
    InvalidRequestStateException,
)
from src.domain.quotation import QuotationId


def test_manual_quotation_request_creation():
    req = ManualQuotationRequest(
        ticket_id="REQ-2026-0001",
        requester_user_id="user_alice",
        department="Manufacturing-T27122",
        item_description="High Precision Servo Motor 400W",
        part_number="SV-400-JIS",
        target_quantity=2.0,
        target_unit="Set",
        needed_by_date=date(2026, 11, 1),
        urgency=RequestUrgency.HIGH,
    )
    assert req.ticket_id == "REQ-2026-0001"
    assert req.status == RequestStatus.SUBMITTED
    assert req.fulfilled_quotation_id is None


def test_manual_quotation_request_empty_description_raises():
    with pytest.raises(ValueError) as excinfo:
        ManualQuotationRequest(
            ticket_id="REQ-2026-0002",
            requester_user_id="user_alice",
            department="Operations",
            item_description="   ",
        )
    assert "Item description cannot be empty" in str(excinfo.value)


def test_manual_quotation_request_fulfillment():
    req = ManualQuotationRequest(
        ticket_id="REQ-2026-0003",
        requester_user_id="user_alice",
        department="Operations",
        item_description="Custom Flange DN50",
    )
    target_quotation = QuotationId("QT-2026-0099")
    req.fulfill(quotation_id=target_quotation, ph_user_id="ph_bob")

    assert req.status == RequestStatus.FULFILLED
    assert req.fulfilled_quotation_id == target_quotation


def test_manual_quotation_request_cannot_fulfill_twice():
    req = ManualQuotationRequest(
        ticket_id="REQ-2026-0004",
        requester_user_id="user_alice",
        department="Operations",
        item_description="Custom Flange DN50",
    )
    req.fulfill(quotation_id=QuotationId("QT-2026-0099"), ph_user_id="ph_bob")

    with pytest.raises(InvalidRequestStateException) as excinfo:
        req.fulfill(quotation_id=QuotationId("QT-2026-0100"), ph_user_id="ph_bob")
    assert "already in FULFILLED state" in str(excinfo.value)
