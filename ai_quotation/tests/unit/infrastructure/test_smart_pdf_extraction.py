import os
from datetime import date
import pytest
from src.infrastructure.pdf_reader import PdfDocumentReader


def test_smart_extraction_dooddee_button_box():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "26DD09113 _ Botton Box  Project M-AL6-001B__ (PMC_Minebea Thai) K. Peerapat.pdf")
    draft = reader.extract_draft(pdf_path)

    # Quotation Number
    assert draft.quotation_number in ["26DD09113", "099-320"]
    # Vendor
    assert "DooDee Technology" in draft.vendor_name
    # Dates
    assert draft.issue_date == date(2026, 9, 25)
    assert draft.expiration_date == date(2026, 10, 25)
    # Items
    assert len(draft.items) >= 1
    first_item = draft.items[0]
    assert "Botton Box" in first_item.description or "Button Box" in first_item.description
    assert first_item.quantity == 12.0
    assert first_item.unit_price == 325.0
    assert first_item.part_number == "BXM47-B1-16"


def test_smart_extraction_iwase():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "26Q13131 (2).pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "26Q13131"
    assert "IWASE" in draft.vendor_name
    assert draft.issue_date == date(2026, 7, 31)
    assert draft.expiration_date == date(2026, 9, 5)
    assert draft.vendor_tax_id == "0105543072502"


def test_smart_extraction_fanuc():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QT NO. 137836.pdf")
    draft = reader.extract_draft(pdf_path)

    assert "137836" in draft.quotation_number
    assert "FANUC" in draft.vendor_name
    assert draft.issue_date == date(2026, 9, 23)
    assert draft.expiration_date == date(2026, 10, 23)


def test_smart_extraction_tornos_validity_range():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "Sales_quotation_0021221998.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "21221998"
    assert "TORNOS" in draft.vendor_name
    assert draft.issue_date == date(2026, 9, 23)
    assert draft.expiration_date == date(2026, 10, 25)


def test_smart_extraction_thai_inter_be_year_and_th_exp():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "416359.pdf")
    draft = reader.extract_draft(pdf_path)

    assert "0416359" in draft.quotation_number
    assert draft.vendor_name == "THAI-INTER ELECTRIC INDUSTRIES CO.,LTD."
    assert "๏" not in draft.vendor_name
    assert draft.issue_date == date(2026, 7, 13)
    assert draft.expiration_date == date(2026, 10, 11)


def test_smart_extraction_factory_max_thai_days():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "69Q-19458.pdf")
    draft = reader.extract_draft(pdf_path)

    assert "69Q" in draft.quotation_number
    assert draft.issue_date == date(2026, 9, 25)
    assert draft.expiration_date == date(2026, 10, 2)


def test_smart_extraction_trisak_validity_days():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "ใบเสนอราคา (1).pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "SQ-126073336"
    assert draft.issue_date == date(2026, 7, 31)
    assert draft.expiration_date == date(2026, 8, 7)


def test_smart_extraction_scanned_citizen_25_334():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "25-334.pdf")
    draft = reader.extract_draft(pdf_path)

    assert "25-334" in draft.quotation_number
    assert "CITIZEN" in draft.vendor_name
    assert draft.issue_date == date(2025, 7, 2)
    assert draft.expiration_date == date(2025, 8, 4)
    assert len(draft.items) >= 1
    assert "MINI CYCLE PUMP" in draft.items[0].description
    assert draft.items[0].unit_price == 17700.0


def test_smart_extraction_amornkahaphant_nmb9623():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "NMB9623.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "NMB9623"
    assert "Amornkahaphant" in draft.vendor_name
    assert draft.issue_date == date(2026, 10, 2)
    assert draft.currency == "THB"
    assert draft.total_amount == 6189.95
    assert len(draft.items) == 17

    # Verify first and notable items
    it1 = draft.items[0]
    assert it1.item_number == 1
    assert "Cap screw SUS M12*25" in it1.description
    assert it1.quantity == 20.0
    assert it1.unit == "Pcs"
    assert it1.unit_price == 16.0
    assert it1.amount == 320.0

    # Item with comma in quantity (1,100)
    it15 = draft.items[14]
    assert it15.item_number == 15
    assert "Cap screw SUS M3*6" in it15.description
    assert it15.quantity == 1100.0
    assert it15.unit == "Pcs"
    assert it15.unit_price == 1.6
    assert it15.amount == 1760.0

    # Item 17
    it17 = draft.items[16]
    assert it17.item_number == 17
    assert "Cap screw SUS M2*4" in it17.description
    assert it17.quantity == 20.0
    assert it17.unit_price == 5.0
    assert it17.amount == 100.0


def test_smart_extraction_thai_inter_419990():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "419990.pdf")
    draft = reader.extract_draft(pdf_path)

    assert "0419990" in draft.quotation_number
    assert draft.vendor_name == "THAI-INTER ELECTRIC INDUSTRIES CO.,LTD."
    assert draft.issue_date == date(2026, 10, 2)
    assert draft.expiration_date == date(2026, 12, 31)
    assert draft.total_amount == 1027.2
    assert len(draft.items) == 2

    # Item 1
    it1 = draft.items[0]
    assert it1.item_number == 1
    assert "Y 1.5-3S" in it1.description
    assert it1.quantity == 700.0
    assert it1.unit == "ตัว"
    assert it1.unit_price == 1.2
    assert it1.amount == 840.0

    # Item 2
    it2 = draft.items[1]
    assert it2.item_number == 2
    assert "R2.5-4" in it2.description
    assert it2.quantity == 100.0
    assert it2.unit == "ตัว"
    assert it2.unit_price == 1.2
    assert it2.amount == 120.0

