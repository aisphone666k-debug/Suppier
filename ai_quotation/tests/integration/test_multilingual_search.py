from datetime import date
import sqlite3
import pytest

from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.infrastructure.search_cache import MemorySearchCache
from src.infrastructure.vector_index import MemoryVectorIndex
from src.infrastructure.embedding_engine import FastEmbedEngine
from src.application.quotation_service import QuotationApplicationService


@pytest.fixture
def service():
    conn = sqlite3.connect(":memory:")
    q_repo = SqliteQuotationRepository(conn)
    q_repo.initialize_schema()

    m_repo = SqliteManualRequestRepository(conn)
    m_repo.initialize_schema()

    cache = MemorySearchCache()
    v_index = MemoryVectorIndex()
    engine = FastEmbedEngine()

    svc = QuotationApplicationService(
        quotation_repository=q_repo,
        manual_request_repository=m_repo,
        search_cache=cache,
        vector_index=v_index,
        embedding_engine=engine,
    )

    today = date(2026, 9, 25)

    # Seed 1: Button Box quotation (Minebea Thai)
    svc.register_quotation(
        quotation_number="099-320",
        vendor_name="DooDee Technology Co.,Ltd.",
        issue_date=today,
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "M-AL6-001B",
                "description": "Button Box Control Unit Project M-AL6-001B (PMC_Minebea Thai)",
                "quantity": 1.0,
                "unit": "Set",
                "unit_price": 15000.0,
            }
        ],
        pdf_path="quoatation/26DD09113.pdf",
        pdf_sha256="sha_box",
        user_role="PH_USER",
    )

    # Seed 2: Bando Belt quotation
    svc.register_quotation(
        quotation_number="137836",
        vendor_name="BANDO CHEMICAL INDUSTRIES (THAILAND) LTD.",
        issue_date=today,
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "A-61(S)",
                "description": "Bando Industrial Transmission V-Belt A-61(S)",
                "quantity": 10.0,
                "unit": "Pcs",
                "unit_price": 513.0,
            }
        ],
        pdf_path="quoatation/BANDO (6).pdf",
        pdf_sha256="sha_belt",
        user_role="PH_USER",
    )

    return svc


def test_search_thai_box_matches_button_box(service):
    """User searches in Thai 'กล่อง' (box) -> matches Button Box."""
    today = date(2026, 9, 25)
    results = service.search(query="กล่อง", user_role="NORMAL_USER", reference_date=today)
    assert len(results) > 0
    top = results[0]
    assert "Button Box" in top.quotation.items[0].description or "099-320" in top.quotation.quotation_number
    assert top.confidence.value >= 0.80


def test_search_japanese_box_kanji(service):
    """User searches in Japanese Kanji '箱' (box) -> matches Button Box."""
    today = date(2026, 9, 25)
    results = service.search(query="箱", user_role="NORMAL_USER", reference_date=today)
    assert len(results) > 0
    top = results[0]
    assert "Button Box" in top.quotation.items[0].description or "099-320" in top.quotation.quotation_number
    assert top.confidence.value >= 0.80


def test_search_japanese_box_katakana(service):
    """User searches in Japanese Katakana 'ボックス' (box) -> matches Button Box."""
    today = date(2026, 9, 25)
    results = service.search(query="ボックス", user_role="NORMAL_USER", reference_date=today)
    assert len(results) > 0
    top = results[0]
    assert "Button Box" in top.quotation.items[0].description
    assert top.confidence.value >= 0.80


def test_search_japanese_belt(service):
    """User searches in Japanese 'ベルト' (belt) -> matches Bando Belt."""
    today = date(2026, 9, 25)
    results = service.search(query="ベルト", user_role="NORMAL_USER", reference_date=today)
    assert len(results) > 0
    top = results[0]
    assert "Bando" in top.quotation.vendor_name or "Belt" in top.quotation.items[0].description
    assert top.confidence.value >= 0.80


def test_search_thai_belt(service):
    """User searches in Thai 'สายพาน' (belt) -> matches Bando Belt."""
    today = date(2026, 9, 25)
    results = service.search(query="สายพาน", user_role="NORMAL_USER", reference_date=today)
    assert len(results) > 0
    top = results[0]
    assert "Bando" in top.quotation.vendor_name or "Belt" in top.quotation.items[0].description
    assert top.confidence.value >= 0.80


def test_search_thai_conceptual_container_finds_button_box(service):
    """User searches in Thai conceptual meaning 'ภาชนะ' (container/receptacle) -> matches Button Box."""
    today = date(2026, 9, 25)
    results = service.search(query="ภาชนะ", user_role="NORMAL_USER", reference_date=today)
    assert len(results) > 0
    top = results[0]
    assert "Button Box" in top.quotation.items[0].description or "099-320" in top.quotation.quotation_number
    assert top.confidence.value >= 0.80
