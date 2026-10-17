from datetime import date
import pytest
from unittest.mock import MagicMock

from src.domain.quotation import Quotation, QuotationId, QuotationItem, QuotationStatus
from src.domain.validity_period import ValidityPeriod
from src.application.inquiry_generator import AnswerGeneratorPort, QuotationChunkContext
from src.application.quotation_inquiry_service import QuotationInquiryService
from src.application.quotation_service import QuotationApplicationService, SearchResultView


class StubAnswerGenerator(AnswerGeneratorPort):
    def __init__(self, canned_answer: str = "Test answer"):
        self.canned_answer = canned_answer
        self.last_query = None
        self.last_chunks = []

    def generate_answer(self, query: str, context_chunks: list[QuotationChunkContext]) -> str:
        self.last_query = query
        self.last_chunks = context_chunks
        return self.canned_answer


@pytest.fixture
def mock_quotation_service():
    service = MagicMock(spec=QuotationApplicationService)
    q1 = Quotation(
        quotation_id=QuotationId("QT-137836"),
        quotation_number="137836",
        vendor_name="Bando Chemical Industries Ltd.",
        validity_period=ValidityPeriod(issue_date=date(2026, 1, 1), expiration_date=date(2026, 12, 31)),
        items=[
            QuotationItem(item_number=1, description="Power Ace V-Belt", quantity=10.0, unit="Pcs", unit_price=450.0, part_number="5V-1400")
        ],
        pdf_path="quoatation/137836.pdf",
        pdf_sha256="sha137836",
        currency="THB",
        status=QuotationStatus.ACTIVE,
    )
    from src.domain.confidence_score import ConfidenceScore
    service.search.return_value = [
        SearchResultView(quotation=q1, confidence=ConfidenceScore(0.95), can_receive=True)
    ]
    return service


def test_inquiry_service_retrieves_quotations_and_generates_grounded_answer(mock_quotation_service):
    generator = StubAnswerGenerator(canned_answer="Bando offers V-Belts at 450 THB.")
    inquiry_service = QuotationInquiryService(
        quotation_service=mock_quotation_service,
        answer_generator=generator,
    )

    answer = inquiry_service.answer_inquiry(query="What is the unit price for Bando V-Belts?")
    assert answer == "Bando offers V-Belts at 450 THB."
    assert generator.last_query == "What is the unit price for Bando V-Belts?"
    assert len(generator.last_chunks) == 1
    assert generator.last_chunks[0].quotation_number == "137836"
    assert "450.0" in generator.last_chunks[0].items_summary


def test_inquiry_service_handles_empty_search_results(mock_quotation_service):
    mock_quotation_service.search.return_value = []
    generator = StubAnswerGenerator()
    inquiry_service = QuotationInquiryService(
        quotation_service=mock_quotation_service,
        answer_generator=generator,
    )

    answer = inquiry_service.answer_inquiry(query="Non-existent part")
    assert "no matching quotation" in answer.lower()
