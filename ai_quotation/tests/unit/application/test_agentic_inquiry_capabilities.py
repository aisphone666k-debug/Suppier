from datetime import date
from unittest.mock import MagicMock
import pytest

from src.domain.quotation import Quotation, QuotationId, QuotationItem, QuotationStatus
from src.domain.validity_period import ValidityPeriod
from src.domain.confidence_score import ConfidenceScore
from src.application.inquiry_generator import AnswerGeneratorPort, QuotationChunkContext
from src.application.quotation_inquiry_service import QuotationInquiryService
from src.application.quotation_service import QuotationApplicationService, SearchResultView


class AgenticRecordingGenerator(AnswerGeneratorPort):
    def __init__(self):
        self.recorded_query = None
        self.recorded_chunks = []

    def generate_answer(self, query: str, context_chunks: list[QuotationChunkContext]) -> str:
        self.recorded_query = query
        self.recorded_chunks = context_chunks
        if "มีอะไรบ้าง" in query or "overview" in query.lower():
            return "ในระบบมีใบเสนอราคาของ Bando (สายพาน) และ DooDee (Button Box)"
        if "เป็นเเบบไหน" in query or "แบบไหน" in query:
            return "สายพานนี้เป็นสายพานร่องวี (V-Belt) รุ่น Power Ace A-61(S) สำหรับส่งกำลังในงานอุตสาหกรรม"
        return "Generic agent answer"


@pytest.fixture
def mock_agentic_quotation_service():
    service = MagicMock(spec=QuotationApplicationService)

    q_belt = Quotation(
        quotation_id=QuotationId("QT-BANDO-01"),
        quotation_number="QT-BANDO-01",
        vendor_name="Bando Chemical Industries (Thailand) Ltd.",
        validity_period=ValidityPeriod(issue_date=date(2026, 1, 1), expiration_date=date(2026, 12, 31)),
        items=[
            QuotationItem(
                item_number=1,
                description="Power Ace Industrial V-Belt",
                quantity=10.0,
                unit="Pcs",
                unit_price=1500.0,
                part_number="A-61(S)",
            )
        ],
        pdf_path="quoatation/bando.pdf",
        pdf_sha256="sha_bando",
        currency="THB",
        status=QuotationStatus.ACTIVE,
        raw_text="Bando Chemical Power Ace High Torque Transmission V-Belt Standard Cross Section A-61(S)",
    )

    q_box = Quotation(
        quotation_id=QuotationId("QT-DOODEE-02"),
        quotation_number="QT-DOODEE-02",
        vendor_name="DooDee Technology Co., Ltd.",
        validity_period=ValidityPeriod(issue_date=date(2026, 1, 1), expiration_date=date(2026, 12, 31)),
        items=[
            QuotationItem(
                item_number=1,
                description="Button Box Control Unit Project",
                quantity=1.0,
                unit="Lot",
                unit_price=25000.0,
                part_number="M-AL6-001B",
            )
        ],
        pdf_path="quoatation/doodee.pdf",
        pdf_sha256="sha_doodee",
        currency="THB",
        status=QuotationStatus.ACTIVE,
        raw_text="DooDee Technology Industrial Aluminum Push Button Enclosure Box M-AL6-001B",
    )

    # For catalog intent (find_all)
    service.quotation_repository = MagicMock()
    service.quotation_repository.find_all.return_value = [q_belt, q_box]

    # For targeted search
    service.search.return_value = [
        SearchResultView(quotation=q_belt, confidence=ConfidenceScore(0.95), can_receive=True)
    ]

    return service


def test_agentic_inquiry_identifies_catalog_overview_intent_in_thai(mock_agentic_quotation_service):
    """When user asks 'มีอะไรบ้าง' in Thai, the agent compiles catalog overview instead of failing search."""
    generator = AgenticRecordingGenerator()
    inquiry_service = QuotationInquiryService(
        quotation_service=mock_agentic_quotation_service,
        answer_generator=generator,
    )

    answer = inquiry_service.answer_inquiry(query="มีอะไรบ้าง")
    assert "Bando" in answer or "DooDee" in answer
    # Chunks should include both quotations from catalog
    assert len(generator.recorded_chunks) >= 2


def test_agentic_inquiry_provides_technical_spec_breakdown(mock_agentic_quotation_service):
    """When user asks 'สายพานนี้เป็นเเบบไหน', the agent provides technical breakdown with raw specs."""
    generator = AgenticRecordingGenerator()
    inquiry_service = QuotationInquiryService(
        quotation_service=mock_agentic_quotation_service,
        answer_generator=generator,
    )

    answer = inquiry_service.answer_inquiry(query="สายพานนี้เป็นเเบบไหน")
    assert "สายพานร่องวี" in answer or "V-Belt" in answer
    assert len(generator.recorded_chunks) >= 1
    # Check that raw text snippet or technical specs were passed to the generator
    assert generator.recorded_chunks[0].raw_text_snippet is not None
    assert "Power Ace" in generator.recorded_chunks[0].raw_text_snippet


def test_agentic_inquiry_generates_interactive_clickable_citation_lines(mock_agentic_quotation_service):
    """The agent formats referenced quotations into structured interactive citation lines for search research."""
    generator = AgenticRecordingGenerator()
    inquiry_service = QuotationInquiryService(
        quotation_service=mock_agentic_quotation_service,
        answer_generator=generator,
    )

    result = inquiry_service.answer_inquiry_with_telemetry(query="สายพานนี้เป็นเเบบไหน")
    assert result.citations is not None
    assert len(result.citations) >= 1

    citation = result.citations[0]
    assert citation.quotation_id == "QT-BANDO-01"
    assert citation.quotation_number == "QT-BANDO-01"
    assert "Bando" in citation.vendor_name
    assert citation.status == "ACTIVE"
    assert "1500" in citation.price_summary
    assert citation.search_query != ""

