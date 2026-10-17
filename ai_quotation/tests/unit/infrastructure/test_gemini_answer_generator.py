import pytest
from unittest.mock import MagicMock, patch
import httpx

from src.infrastructure.gemini_answer_generator import GeminiAnswerGenerator, GeminiApiException
from src.application.inquiry_generator import QuotationChunkContext


def test_gemini_generator_initialization_from_key():
    gen = GeminiAnswerGenerator(api_key="test_key_123", model_name="gemini-1.5-flash")
    assert gen.api_key == "test_key_123"
    assert gen.model_name == "gemini-1.5-flash"


def test_gemini_generator_formats_prompt_and_calls_api():
    gen = GeminiAnswerGenerator(api_key="valid_key", model_name="gemini-1.5-flash")
    chunks = [
        QuotationChunkContext(
            quotation_number="137836",
            vendor_name="Bando Chemical Industries Ltd.",
            currency="THB",
            items_summary="Power Ace V-Belt (Qty: 10 Pcs, Unit Price: 450.0 THB)",
            validity_summary="Valid until 2026-12-31 (ACTIVE)",
        )
    ]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Bando Chemical Industries Ltd. offers Power Ace V-Belt at 450.0 THB per piece."}
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        answer = gen.generate_answer(query="What is the price of Bando belt?", context_chunks=chunks)
        assert "450.0 THB" in answer
        assert mock_post.called


def test_gemini_generator_handles_api_disabled_with_helpful_message():
    gen = GeminiAnswerGenerator(api_key="disabled_key", model_name="gemini-1.5-flash")
    chunks = []

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {
            "code": 403,
            "message": "Gemini API has not been used in project 220466210842 before or it is disabled.",
            "status": "PERMISSION_DENIED",
        }
    }

    with patch("httpx.Client.post", return_value=mock_response):
        with pytest.raises(GeminiApiException) as exc_info:
            gen.generate_answer(query="Hello", context_chunks=chunks)
        assert "disabled" in str(exc_info.value).lower()
