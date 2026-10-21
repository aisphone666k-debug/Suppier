from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class DraftItem:
    """Line item candidate extracted from quotation document."""
    item_number: int
    description: str
    quantity: float
    unit: str
    unit_price: float
    part_number: Optional[str] = None
    amount: Optional[float] = None
    drawing_number: Optional[str] = None


@dataclass(frozen=True)
class ExtractedQuotationDraft:
    """Candidate quotation automatically extracted from an uploaded document."""
    file_path: str
    sha256: str
    quotation_number: str
    vendor_name: str
    issue_date: date
    expiration_date: date
    currency: str
    items: tuple[DraftItem, ...]
    vendor_tax_id: Optional[str] = None
    total_amount: Optional[float] = None
    raw_text: Optional[str] = None
    confidence_score: float = 1.0
