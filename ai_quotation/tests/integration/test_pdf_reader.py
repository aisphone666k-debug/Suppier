import os
import pytest

from src.infrastructure.pdf_reader import PdfDocumentReader, CorruptPdfDocumentException


def test_pdf_reader_extracts_from_sample():
    reader = PdfDocumentReader()
    sample_path = "quoatation/QT NO. 137836.pdf"
    assert os.path.exists(sample_path), "Sample PDF should exist"

    extracted = reader.extract(sample_path)
    assert extracted.file_path == sample_path
    assert len(extracted.sha256) == 64
    assert len(extracted.raw_text) > 0
    # The document contains quotation text
    assert "137836" in extracted.raw_text or "QUOTATION" in extracted.raw_text.upper()


def test_pdf_reader_fails_fast_on_missing_file():
    reader = PdfDocumentReader()
    with pytest.raises(FileNotFoundError):
        reader.extract("quoatation/non_existent_file.pdf")
