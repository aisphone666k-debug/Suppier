from datetime import date
import pytest
from src.domain.validity_period import ValidityPeriod, InvalidValidityPeriodException


def test_validity_period_creation_succeeds_when_expiration_after_issue():
    issue = date(2026, 1, 1)
    expiration = date(2026, 12, 31)
    period = ValidityPeriod(issue_date=issue, expiration_date=expiration)
    assert period.issue_date == issue
    assert period.expiration_date == expiration


def test_validity_period_creation_succeeds_when_expiration_equals_issue():
    today = date(2026, 9, 25)
    period = ValidityPeriod(issue_date=today, expiration_date=today)
    assert period.is_expired(reference_date=today) is False


def test_validity_period_raises_when_expiration_before_issue():
    issue = date(2026, 12, 31)
    expiration = date(2026, 1, 1)
    with pytest.raises(InvalidValidityPeriodException) as excinfo:
        ValidityPeriod(issue_date=issue, expiration_date=expiration)
    assert "cannot precede issue date" in str(excinfo.value)


def test_validity_period_identifies_expired_state():
    period = ValidityPeriod(issue_date=date(2026, 1, 1), expiration_date=date(2026, 6, 30))
    # On or before expiration date is NOT expired
    assert period.is_expired(reference_date=date(2026, 6, 30)) is False
    # Strictly after expiration date IS expired
    assert period.is_expired(reference_date=date(2026, 7, 1)) is True


def test_validity_period_calculates_days_remaining():
    period = ValidityPeriod(issue_date=date(2026, 9, 1), expiration_date=date(2026, 9, 30))
    assert period.days_remaining(reference_date=date(2026, 9, 25)) == 5
    assert period.days_remaining(reference_date=date(2026, 10, 5)) == -5
