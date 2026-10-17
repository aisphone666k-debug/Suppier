from datetime import date
import sqlite3
import pytest

from src.domain.quotation import Quotation, QuotationId, QuotationStatus, QuotationItem, QuotationAcknowledgment
from src.domain.validity_period import ValidityPeriod
from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository


@pytest.fixture
def repo():
    # In-memory SQLite for high-speed isolated tests
    conn = sqlite3.connect(":memory:")
    repo = SqliteQuotationRepository(conn)
    repo.initialize_schema()
    return repo


def build_sample_quotation(
    qid: str = "QT-137836",
    status: QuotationStatus = QuotationStatus.ACTIVE,
    issue_date: date = date(2026, 1, 1),
    expiration_date: date = date(2026, 12, 31),
) -> Quotation:
    return Quotation(
        quotation_id=QuotationId(qid),
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
        raw_text="Bando Chemical Industrial V-Belt 5V-1400 high power transmission",
    )


def test_save_and_find_by_id(repo):
    q = build_sample_quotation()
    repo.save(q)

    fetched = repo.find_by_id(QuotationId("QT-137836"))
    assert fetched is not None
    assert fetched.quotation_id == q.quotation_id
    assert fetched.vendor_name == "Bando Chemical Industries Ltd."
    assert len(fetched.items) == 1
    assert fetched.items[0].part_number == "5V-1400"
    assert fetched.total_amount == 4500.0


def test_find_expired_and_active(repo):
    active_q = build_sample_quotation("QT-ACTIVE", status=QuotationStatus.ACTIVE, expiration_date=date(2026, 12, 31))
    expired_q = build_sample_quotation(
        "QT-EXPIRED",
        status=QuotationStatus.EXPIRED,
        issue_date=date(2025, 1, 1),
        expiration_date=date(2025, 12, 31),
    )
    repo.save(active_q)
    repo.save(expired_q)

    today = date(2026, 9, 25)
    expired_list = repo.find_expired(reference_date=today)
    assert len(expired_list) == 1
    assert expired_list[0].quotation_id == QuotationId("QT-EXPIRED")

    active_list = repo.find_active(reference_date=today)
    assert len(active_list) == 1
    assert active_list[0].quotation_id == QuotationId("QT-ACTIVE")


def test_record_and_get_acknowledgment(repo):
    q = build_sample_quotation()
    repo.save(q)

    ack = QuotationAcknowledgment(
        quotation_id=q.quotation_id,
        user_id="user_charlie",
        received_date=date(2026, 9, 25),
    )
    repo.record_acknowledgment(ack)

    acks = repo.get_acknowledgments(q.quotation_id)
    assert len(acks) == 1
    assert acks[0].user_id == "user_charlie"
