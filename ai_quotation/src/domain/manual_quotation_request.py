from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from src.domain.quotation import QuotationId


class RequestStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"


class RequestUrgency(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvalidRequestStateException(RuntimeError):
    """Raised when an operation cannot be performed due to request lifecycle state."""
    pass


@dataclass
class ManualQuotationRequest:
    ticket_id: str
    requester_user_id: str
    department: str
    item_description: str
    part_number: Optional[str] = None
    target_quantity: Optional[float] = None
    target_unit: Optional[str] = None
    needed_by_date: Optional[date] = None
    urgency: RequestUrgency = RequestUrgency.NORMAL
    status: RequestStatus = RequestStatus.SUBMITTED
    fulfilled_quotation_id: Optional[QuotationId] = None
    assigned_ph_user_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.item_description or not self.item_description.strip():
            raise ValueError("Item description cannot be empty")
        if not self.ticket_id or not self.ticket_id.strip():
            raise ValueError("Ticket ID cannot be empty")
        if self.target_quantity is not None and self.target_quantity <= 0:
            raise ValueError("Target quantity must be strictly positive")

    def assign_to_review(self, ph_user_id: str) -> None:
        if self.status != RequestStatus.SUBMITTED:
            raise InvalidRequestStateException(f"Cannot assign request in {self.status.value} state")
        self.status = RequestStatus.IN_REVIEW
        self.assigned_ph_user_id = ph_user_id

    def fulfill(self, quotation_id: QuotationId, ph_user_id: str) -> None:
        if self.status in (RequestStatus.FULFILLED, RequestStatus.REJECTED):
            raise InvalidRequestStateException(f"Request is already in {self.status.value} state")
        self.status = RequestStatus.FULFILLED
        self.fulfilled_quotation_id = quotation_id
        self.assigned_ph_user_id = ph_user_id

    def reject(self, reason: str, ph_user_id: str) -> None:
        if self.status in (RequestStatus.FULFILLED, RequestStatus.REJECTED):
            raise InvalidRequestStateException(f"Request is already in {self.status.value} state")
        if not reason or not reason.strip():
            raise ValueError("Rejection reason must be provided")
        self.status = RequestStatus.REJECTED
        self.rejection_reason = reason
        self.assigned_ph_user_id = ph_user_id
