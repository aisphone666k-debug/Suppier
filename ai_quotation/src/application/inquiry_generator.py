from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class QuotationCitationView:
    quotation_id: str
    quotation_number: str
    vendor_name: str
    items_summary: str
    price_summary: str
    status: str
    search_query: str


@dataclass(frozen=True)
class QuotationChunkContext:
    quotation_number: str
    vendor_name: str
    currency: str
    items_summary: str
    validity_summary: str
    quotation_id: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    raw_text_snippet: Optional[str] = None


class AnswerGeneratorPort(ABC):
    """Port for generating natural language answers grounded in quotation context."""

    @abstractmethod
    def generate_answer(self, query: str, context_chunks: list[QuotationChunkContext]) -> str:
        """Generates an answer based strictly on the provided quotation context chunks."""
        pass
