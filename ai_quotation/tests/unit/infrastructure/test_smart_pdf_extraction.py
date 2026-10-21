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
    assert len(draft.items) == 1
    it = draft.items[0]
    assert it.item_number == 1
    assert it.description == "Belt 7M 1360 / Gate"
    assert it.quantity == 3.0
    assert it.unit == "PCS"
    assert it.unit_price == 500.0
    assert it.amount == 1500.0


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
    assert len(draft.items) == 2

    # Item 1: NSKT-4502 NSK [AL-M1202] AIR LINE KIT
    it1 = draft.items[0]
    assert it1.item_number == 1
    assert it1.part_number == "NSKT-4502"
    assert "NSK [AL-M1202] AIR LINE KIT" in it1.description
    assert it1.quantity == 1.0
    assert it1.unit == "Unit"
    assert it1.unit_price == 16458.0
    assert it1.amount == 16458.0

    # Item 2: NSKT-7825 NSK [MSS-1908RA] AIR MOTOR SPINDLE
    it2 = draft.items[1]
    assert it2.item_number == 2
    assert it2.part_number == "NSKT-7825"
    assert "NSK [MSS-1908RA] AIR MOTOR SPINDLE" in it2.description
    assert it2.quantity == 1.0
    assert it2.unit == "Unit"
    assert it2.unit_price == 56784.0
    assert it2.amount == 56784.0

    assert draft.total_amount == 73242.0


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


def test_smart_extraction_lopburi_ruamchang_cnc():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QT-CNC-2026_2525.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "QT-CNC-2026/2525"
    assert draft.vendor_name == "Lopburi Ruamchang CNC Co.,Ltd."
    assert draft.issue_date == date(2026, 9, 30)
    assert draft.expiration_date == date(2026, 10, 30)
    assert draft.total_amount == 6955.0
    assert len(draft.items) == 2

    it1 = draft.items[0]
    assert it1.item_number == 1
    assert it1.description == "INDEPENDENT HOLDER-1"
    assert it1.part_number == "TGM-16-025B-01 R.1"
    assert it1.quantity == 2.0
    assert it1.unit == "PIECE"
    assert it1.unit_price == 2950.0
    assert it1.amount == 5900.0

    it2 = draft.items[1]
    assert it2.item_number == 2
    assert it2.description == "KEY PIN"
    assert it2.part_number == "TGM-16-025B-06 R.1"
    assert it2.quantity == 2.0
    assert it2.unit == "PIECE"
    assert it2.unit_price == 300.0
    assert it2.amount == 600.0


def test_smart_extraction_max_value_technology():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QTH25030116.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "QTH25030116"
    assert "Max Value Technology" in draft.vendor_name
    assert draft.issue_date == date(2025, 3, 14)
    assert draft.expiration_date == date(2025, 4, 13)
    assert draft.total_amount == 185358.24
    assert len(draft.items) == 9

    it1 = draft.items[0]
    assert it1.item_number == 1
    assert "DIATEST" in it1.description
    assert it1.part_number == "BMD-S4-3.00"
    assert it1.quantity == 1.0
    assert it1.unit == "Pce"
    assert it1.unit_price == 22100.0
    assert it1.amount == 17680.0

    it3 = draft.items[2]
    assert it3.item_number == 3
    assert "DIATEST" in it3.description
    assert it3.part_number == "BMD-S4-S-FB-4.70"
    assert it3.quantity == 1.0
    assert it3.unit == "Pce"
    assert it3.unit_price == 24620.0
    assert it3.amount == 19696.0

    it9 = draft.items[8]
    assert it9.item_number == 9
    assert "DIATEST" in it9.description
    assert it9.part_number == "BMD-S4-S-FB-4.61"
    assert it9.quantity == 1.0
    assert it9.unit_price == 24620.0
    assert it9.amount == 19696.0


def test_smart_extraction_tkk_corporation():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QTH_25052990_TKK.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "QTH/25052990"
    assert "TKK CORPORATION" in draft.vendor_name
    assert draft.issue_date == date(2025, 5, 19)
    assert draft.expiration_date == date(2025, 6, 18)
    assert draft.total_amount == 1677.76
    assert len(draft.items) == 1

    it = draft.items[0]
    assert it.item_number == 1
    assert "SAN-EI TECH" in it.description
    assert it.part_number == "SH18TT-B"
    assert it.quantity == 1.0
    assert it.unit == "PC"
    assert it.unit_price == 1600.0
    assert it.amount == 1568.0


def test_smart_extraction_minebeamitsumi_ptd():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QTPTD20240327T_03_PMA.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "QTPTD20240327T-03-PMA"
    assert "Precision Tool & Die" in draft.vendor_name
    assert draft.issue_date == date(2024, 3, 27)
    assert draft.total_amount == 7800.0
    assert len(draft.items) == 1

    it = draft.items[0]
    assert it.item_number == 1
    assert it.part_number == "TGM-02-411C-01 Rev.1"
    assert "V-PLATE" in it.description
    assert it.quantity == 1.0
    assert it.unit == "PCS"
    assert it.unit_price == 7800.0
    assert it.amount == 7800.0


def test_smart_extraction_qtptd_wrapped_row():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QTPTD20241127-T-02.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "QTPTD20241127-T-02"
    assert "Precision Tool & Die" in draft.vendor_name
    assert draft.issue_date == date(2024, 11, 27)
    assert draft.total_amount == 1600.0
    assert len(draft.items) == 2

    it1 = draft.items[0]
    assert it1.item_number == 1
    assert it1.part_number == "TPMA-17CL-002R01-65"
    assert it1.description == "PICK UP COLLET REWORK"
    assert it1.quantity == 1.0
    assert it1.unit == "PCS"
    assert it1.unit_price == 800.0
    assert it1.amount == 800.0

    it2 = draft.items[1]
    assert it2.item_number == 2
    assert it2.part_number == "TPMA-13CL-005-XX"
    assert "SPINDLE COLLET HI-GRIP" in it2.description
    assert it2.quantity == 1.0
    assert it2.unit == "PCS"
    assert it2.unit_price == 800.0
    assert it2.amount == 800.0


def test_smart_extraction_keiaisha_goods_code():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "QU2508-00635_KEIAISHA.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "QU2508-00635"
    assert draft.vendor_name == "KEIAISHA (THAILAND) CO.,LTD."
    assert draft.vendor_tax_id == "0105553038242"
    assert draft.issue_date == date(2025, 8, 28)
    assert draft.expiration_date == date(2025, 10, 27)
    assert draft.total_amount == 7864.50
    assert len(draft.items) == 1

    it = draft.items[0]
    assert it.item_number == 1
    assert it.part_number == "Q2025080131"
    assert "3D PRINTING SERVICE" in it.description
    assert "PHROZEN TOUGH 100E" in it.description
    assert it.quantity == 1.0
    assert it.unit == "Set"
    assert it.unit_price == 7350.0
    assert it.amount == 7350.0


def test_smart_extraction_rinthong_price_first_table():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "6906048_RINTHONG.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "6906048"
    assert draft.vendor_name == "RINTHONG TRADING LTD."
    assert draft.issue_date == date(2026, 6, 23)
    assert draft.expiration_date == date(2026, 7, 23)
    assert draft.total_amount == 365.0
    assert len(draft.items) == 4

    assert draft.items[0].item_number == 1
    assert draft.items[0].description == "SUS.FLAT SCREW M4x8"
    assert draft.items[0].unit_price == 0.70
    assert draft.items[0].quantity == 100.0
    assert draft.items[0].unit == "PCS"
    assert draft.items[0].amount == 70.0

    assert draft.items[1].item_number == 2
    assert draft.items[1].description == "SUS.FLAT SCREW M5x8"
    assert draft.items[1].unit_price == 1.30
    assert draft.items[1].quantity == 100.0
    assert draft.items[1].unit == "PCS"
    assert draft.items[1].amount == 130.0

    assert draft.items[2].item_number == 3
    assert draft.items[2].description == "SUS.TRUSS SCREW M4x10"
    assert draft.items[2].unit_price == 0.90
    assert draft.items[2].quantity == 100.0
    assert draft.items[2].unit == "PCS"
    assert draft.items[2].amount == 90.0

    assert draft.items[3].item_number == 4
    assert draft.items[3].description == "SUS.TRUSS SCREW M4x6"
    assert draft.items[3].unit_price == 0.75
    assert draft.items[3].quantity == 100.0
    assert draft.items[3].unit == "PCS"
    assert draft.items[3].amount == 75.0


def test_smart_extraction_mitsubishi_type3_font():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "Quotation Net (FA25040029).pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "FA25040029"
    assert "MITSUBISHI ELECTRIC FACTORY AUTOMATION" in draft.vendor_name
    assert draft.issue_date == date(2025, 4, 1)
    assert draft.expiration_date == date(2025, 4, 30)
    assert draft.total_amount == 48260.21
    assert draft.currency == "THB"
    assert len(draft.items) == 10

    # Item 1
    assert draft.items[0].item_number == 1
    assert draft.items[0].part_number == "NV32-SVF"
    assert draft.items[0].unit_price == 1303.0
    assert draft.items[0].quantity == 2.0
    assert draft.items[0].amount == 2606.0

    # Item 3
    assert draft.items[2].item_number == 3
    assert draft.items[2].part_number == "Q03UDVCPU"
    assert draft.items[2].unit_price == 11140.0
    assert draft.items[2].quantity == 1.0
    assert draft.items[2].amount == 11140.0

    # Item 10
    assert draft.items[9].item_number == 10
    assert draft.items[9].part_number == "GT09-C30USB-5P"
    assert draft.items[9].unit_price == 2732.0
    assert draft.items[9].quantity == 1.0
    assert draft.items[9].amount == 2732.0


def test_smart_extraction_visco_package_bom():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "S25000425_VISCO.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "S25000425"
    assert "ViSCO Technologies" in draft.vendor_name
    assert draft.issue_date == date(2025, 7, 9)
    assert draft.expiration_date == date(2025, 8, 8)
    assert draft.currency == "THB"
    assert draft.total_amount == 577800.0
    assert len(draft.items) == 12

    # Check first item
    assert draft.items[0].item_number == 1
    assert draft.items[0].part_number == "V9KTDPL8-4MV"
    assert draft.items[0].description == "VTV-9000mini-qc-4C SSD"
    assert draft.items[0].quantity == 1.0

    # Check middle item
    assert draft.items[4].item_number == 5
    assert draft.items[4].part_number == "POWERCABLE-1.8"
    assert draft.items[4].description == "POWER CABLE 1.8m YP12+YC12"
    assert draft.items[4].quantity == 2.0

    # Check last item
    assert draft.items[11].item_number == 12
    assert draft.items[11].part_number == "QCS-CSL-U00"
    assert draft.items[11].description == "VTV-QCS dongle"
    assert draft.items[11].quantity == 1.0


def test_smart_extraction_vs_product_dwg():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("quoatation", "VS25-1540_VS_PRODUCT.pdf")
    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "VS25-1540"
    assert draft.vendor_name == "V S Product and Supply Co.,Ltd."
    assert draft.issue_date == date(2025, 8, 22)
    assert draft.expiration_date == date(2025, 9, 21)
    assert draft.currency == "THB"
    assert draft.total_amount == 46866.0
    assert len(draft.items) == 19

    # Check item 1
    it1 = draft.items[0]
    assert it1.item_number == 1
    assert it1.description == "V-BLOCK"
    assert it1.drawing_number == "TGM02003A01"
    assert it1.part_number == "TGM02003A01"
    assert it1.quantity == 1.0
    assert it1.unit == "PCS"
    assert it1.unit_price == 1740.0
    assert it1.amount == 1740.0

    # Check item 2
    it2 = draft.items[1]
    assert it2.item_number == 2
    assert it2.description == "V-BLOCK"
    assert it2.drawing_number == "TGM02003A02"
    assert it2.part_number == "TGM02003A02"
    assert it2.unit_price == 3600.0

    # Check item 19 (ensure footnote didn't pollute description)
    it19 = draft.items[18]
    assert it19.item_number == 19
    assert it19.description == "V-BLOCK"
    assert it19.drawing_number == "TGM02003A20"
    assert it19.part_number == "TGM02003A20"
    assert it19.unit_price == 2050.0


def test_smart_extraction_pcrg_cleanroom_price_agreement():
    reader = PdfDocumentReader()
    pdf_path = os.path.join("storage", "staging", "stage_9004b642_ราคาชุดคลีนรูม PCRG.pdf")
    if not os.path.exists(pdf_path):
        import glob
        matches = glob.glob("storage/staging/*PCRG*.pdf")
        if matches:
            pdf_path = matches[0]
        else:
            pytest.skip("PCRG test PDF not present in environment")

    draft = reader.extract_draft(pdf_path)

    assert draft.quotation_number == "CDS65/07/045"
    assert "PCRG" in draft.vendor_name
    assert draft.issue_date == date(2022, 8, 15)
    assert len(draft.items) == 16

    # Verify key items across categories (Suits, Gowns, Aprons, Accessories)
    it1 = draft.items[0]
    assert it1.item_number == 1
    assert it1.part_number == "16-05CS"
    assert "CR.Suit" in it1.description
    assert it1.quantity == 1.0
    assert it1.unit == "SET"
    assert it1.unit_price == 365.0
    assert it1.amount == 365.0

    it4 = draft.items[3]
    assert it4.item_number == 4
    assert it4.part_number == "16-CRGNHB"
    assert "Cleanroom Gown" in it4.description
    assert it4.unit == "PCS"
    assert it4.unit_price == 290.0

    it7 = draft.items[6]
    assert it7.item_number == 7
    assert it7.part_number == "16-CRAPLB"
    assert "Cleanroom Apron" in it7.description
    assert it7.unit == "PCS"
    assert it7.unit_price == 85.0

    it10 = draft.items[9]
    assert it10.item_number == 10
    assert it10.part_number == "CRHD"
    assert "Hood" in it10.description
    assert it10.unit == "PCS"
    assert it10.unit_price == 105.0

    it11 = draft.items[10]
    assert it11.item_number == 11
    assert it11.part_number == "CRMKBR"
    assert "Mask" in it11.description
    assert it11.unit == "PCS"
    assert it11.unit_price == 28.0

    it13 = draft.items[12]
    assert it13.item_number == 13
    assert it13.part_number == "CRBT"
    assert "Booties" in it13.description
    assert it13.unit == "PRS"
    assert it13.unit_price == 160.0

    it14 = draft.items[13]
    assert it14.item_number == 14
    assert it14.part_number == "CRCBT"
    assert "Cover Booties" in it14.description
    assert it14.unit == "PRS"
    assert it14.unit_price == 135.0

    it16 = draft.items[15]
    assert it16.item_number == 16
    assert it16.part_number == "CRSKMA"
    assert "Sock With net" in it16.description
    assert it16.unit == "PRS"
    assert it16.unit_price == 115.0

    assert draft.total_amount == 3228.0












