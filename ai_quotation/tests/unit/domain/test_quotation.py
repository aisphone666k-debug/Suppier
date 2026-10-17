from datetime import date
import pytest

from src.domain.quotation import (
    Quotation,
    QuotationId,
    QuotationStatus,
    QuotationItem,
    InvalidQuotationStateException,
    QuotationExpiredException,
)
from src.domain.validity_period import ValidityPeriod, InvalidValidityPeriodException


def build_sample_quotation(
    status: QuotationStatus = QuotationStatus.ACTIVE,
    issue_date: date = date(2026, 1, 1),
    expiration_date: date = date(2026, 12, 31),
) -> Quotation:
    return Quotation(
        quotation_id=QuotationId("QT-137836"),
        quotation_number="137836",
        vendor_name="Bando Chemical Industries Ltd.",
        validity_period=ValidityPeriod(issue_date=issue_date, expiration_date=expiration_date),
        status=status,
        items=(
            QuotationItem(
                item_number=1,
                part_number="5V-1400",
                description="Power Ace V-Belt",
                quantity=10.0,
                unit="Pcs",
                unit_price=450.0,
            ),
        ),
        pdf_path="storage/pdf/QT NO. 137836.pdf",
        pdf_sha256="abc123sha256",
        currency="THB",
    )


def test_quotation_creation_and_properties():
    quotation = build_sample_quotation()
    assert str(quotation.quotation_id) == "QT-137836"
    assert quotation.vendor_name == "Bando Chemical Industries Ltd."
    assert quotation.total_amount == 4500.0
    assert quotation.status == QuotationStatus.ACTIVE


def test_quotation_receive_succeeds_when_active():
    quotation = build_sample_quotation()
    today = date(2026, 9, 25)
    ack = quotation.receive(user_id="user_john", reference_date=today)
    assert ack.quotation_id == quotation.quotation_id
    assert ack.user_id == "user_john"
    assert ack.received_date == today


def test_quotation_receive_fails_when_expired():
    expired_quotation = build_sample_quotation(
        status=QuotationStatus.ACTIVE,
        issue_date=date(2025, 1, 1),
        expiration_date=date(2026, 1, 1),
    )
    today = date(2026, 9, 25)
    # Status should auto-evaluate to EXPIRED
    expired_quotation.evaluate_expiration(reference_date=today)
    assert expired_quotation.status == QuotationStatus.EXPIRED

    with pytest.raises(QuotationExpiredException) as excinfo:
        expired_quotation.receive(user_id="user_john", reference_date=today)
    assert "Cannot receive expired quotation" in str(excinfo.value)


def test_quotation_renewal_by_ph_succeeds_with_future_date():
    quotation = build_sample_quotation(
        status=QuotationStatus.EXPIRED,
        issue_date=date(2025, 1, 1),
        expiration_date=date(2026, 1, 1),
    )
    today = date(2026, 9, 25)
    new_expiration = date(2027, 6, 30)

    event = quotation.renew(new_expiration_date=new_expiration, reference_date=today, remarks="Vendor extension")

    assert quotation.status == QuotationStatus.ACTIVE
    assert quotation.validity_period.expiration_date == new_expiration
    assert event.quotation_id == quotation.quotation_id
    assert event.new_expiration_date == new_expiration


def test_quotation_renewal_fails_with_past_or_current_date():
    quotation = build_sample_quotation(
        status=QuotationStatus.EXPIRED,
        issue_date=date(2025, 1, 1),
        expiration_date=date(2026, 1, 1),
    )
    today = date(2026, 9, 25)
    past_date = date(2026, 9, 20)

    with pytest.raises(InvalidValidityPeriodException) as excinfo:
        quotation.renew(new_expiration_date=past_date, reference_date=today, remarks="Invalid past date")
    assert "must be strictly in the future" in str(excinfo.value)
