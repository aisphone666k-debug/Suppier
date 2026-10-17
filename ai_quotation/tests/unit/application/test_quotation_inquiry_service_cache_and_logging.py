from datetime import date
from unittest.mock import MagicMock
import pytest

from src.domain.quotation import Quotation, QuotationId, QuotationItem, QuotationStatus
from src.domain.validity_period import ValidityPeriod
from src.domain.confidence_score import ConfidenceScore
from src.application.inquiry_generator import AnswerGeneratorPort, QuotationChunkContext
from src.application.quotation_inquiry_service import QuotationInquiryService, InquiryResultView
from src.application.quotation_service import QuotationApplicationService, SearchResultView
from src.infrastructure.inquiry_cache import MemoryInquiryCache


class CountingAnswerGenerator(AnswerGeneratorPort):
    def __init__(self):
        self.call_count = 0

    def generate_answer(self, query: str, context_chunks: list[QuotationChunkContext]) -> str:
        self.call_count += 1
        return f"Generated answer for {query}"


@pytest.fixture
def mock_quotation_service():
    service = MagicMock(spec=QuotationApplicationService)
    q1 = Quotation(
        quotation_id=QuotationId("QT-137836"),
        quotation_number="137836",
        vendor_name="Bando Chemical Industries Ltd.",
        validity_period=ValidityPeriod(issue_date=date(2026, 1, 1), expiration_date=date(2026, 12, 31)),
        items=[
            QuotationItem(item_number=1, description="Power Ace V-Belt", quantity=10.0, unit="Pcs", unit_price=450.0)
        ],
        pdf_path="quoatation/137836.pdf",
        pdf_sha256="sha137836",
        currency="THB",
        status=QuotationStatus.ACTIVE,
    )
    service.search.return_value = [
        SearchResultView(quotation=q1, confidence=ConfidenceScore(0.95), can_receive=True)
    ]
    return service


def test_inquiry_service_serves_repeated_queries_from_cache(mock_quotation_service):
    generator = CountingAnswerGenerator()
    cache = MemoryInquiryCache(ttl_seconds=300)
    inquiry_service = QuotationInquiryService(
        quotation_service=mock_quotation_service,
        answer_generator=generator,
        inquiry_cache=cache,
    )

    # First call: Cache miss -> invokes generator
    result_1: InquiryResultView = inquiry_service.answer_inquiry_with_telemetry("What is the price of belt?")
    assert result_1.cached is False
    assert result_1.answer == "Generated answer for What is the price of belt?"
    assert generator.call_count == 1
    assert result_1.total_duration_ms >= 0

    # Second call: Cache hit -> returns cached without invoking generator!
    result_2: InquiryResultView = inquiry_service.answer_inquiry_with_telemetry("What is the price of belt?")
    assert result_2.cached is True
    assert result_2.answer == "Generated answer for What is the price of belt?"
    assert generator.call_count == 1  # Generator was NOT called again!
    assert result_2.total_duration_ms < result_1.total_duration_ms or result_2.total_duration_ms < 5.0
