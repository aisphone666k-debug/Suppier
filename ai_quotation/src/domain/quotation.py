from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from src.domain.validity_period import ValidityPeriod, InvalidValidityPeriodException


class QuotationStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class QuotationExpiredException(RuntimeError):
    """Raised when an operation cannot be performed on an expired quotation."""
    pass


class InvalidQuotationStateException(RuntimeError):
    """Raised when an operation is invalid for current quotation state."""
    pass


@dataclass(frozen=True)
class QuotationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("QuotationId cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class QuotationItem:
    item_number: int
    description: str
    quantity: float
    unit: str
    unit_price: float
    part_number: Optional[str] = None

    @property
    def total_price(self) -> float:
        return round(self.quantity * self.unit_price, 4)


@dataclass(frozen=True)
class QuotationAcknowledgment:
    quotation_id: QuotationId
    user_id: str
    received_date: date


@dataclass(frozen=True)
class QuotationRenewedEvent:
    quotation_id: QuotationId
    new_expiration_date: date
    renewed_date: date
    remarks: str


@dataclass
class Quotation:
    quotation_id: QuotationId
    quotation_number: str
    vendor_name: str
    validity_period: ValidityPeriod
    status: QuotationStatus
    items: tuple[QuotationItem, ...]
    pdf_path: str
    pdf_sha256: str
    currency: str = "THB"
    vendor_tax_id: Optional[str] = None
    raw_text: Optional[str] = None

    @property
    def total_amount(self) -> float:
        return round(sum(item.total_price for item in self.items), 4)

    def evaluate_expiration(self, reference_date: date) -> QuotationStatus:
        """Evaluates and transitions to EXPIRED if current date surpasses validity period."""
        if self.status == QuotationStatus.ACTIVE and self.validity_period.is_expired(reference_date):
            self.status = QuotationStatus.EXPIRED
        return self.status

    def can_be_received(self, reference_date: date) -> bool:
        self.evaluate_expiration(reference_date)
        return self.status == QuotationStatus.ACTIVE

    def receive(self, user_id: str, reference_date: date) -> QuotationAcknowledgment:
        """Normal User claims/acknowledges quotation demand."""
        self.evaluate_expiration(reference_date)
        if self.status == QuotationStatus.EXPIRED:
            raise QuotationExpiredException(
                f"Cannot receive expired quotation {self.quotation_id} (expired on {self.validity_period.expiration_date})"
            )
        if self.status != QuotationStatus.ACTIVE:
            raise InvalidQuotationStateException(
                f"Quotation {self.quotation_id} is in state {self.status}, cannot be received"
            )
        return QuotationAcknowledgment(
            quotation_id=self.quotation_id,
            user_id=user_id,
            received_date=reference_date,
        )

    def renew(self, new_expiration_date: date, reference_date: date, remarks: str) -> QuotationRenewedEvent:
        """PH User extends validity date and restores status to ACTIVE."""
        if new_expiration_date <= reference_date:
            raise InvalidValidityPeriodException(
                f"Renewal expiration date ({new_expiration_date}) must be strictly in the future relative to {reference_date}"
            )

        self.validity_period = ValidityPeriod(
            issue_date=self.validity_period.issue_date,
            expiration_date=new_expiration_date,
        )
        self.status = QuotationStatus.ACTIVE

        return QuotationRenewedEvent(
            quotation_id=self.quotation_id,
            new_expiration_date=new_expiration_date,
            renewed_date=reference_date,
            remarks=remarks,
        )
