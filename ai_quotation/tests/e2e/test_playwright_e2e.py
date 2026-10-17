import re
import pytest
from playwright.sync_api import Page, expect


def test_e2e_search_and_click_interactions(page: Page):
    # 1. Open the homepage
    page.goto("http://127.0.0.1:8000/")
    expect(page).to_have_title(re.compile("QuotationFinder"))

    search_input = page.locator("#search-input")
    expect(search_input).to_be_visible()

    # 2. Type "bando" into the search bar
    search_input.fill("bando")

    # 3. Verify search results table renders with BANDO
    results_table = page.locator("#search-results table")
    expect(results_table).to_be_visible(timeout=5000)
    expect(page.locator("text=BANDO CHEMICAL INDUSTRIES")).to_be_visible()
    expect(page.locator("text=98.0%")).to_be_visible()

    # 4. Click [Review PDF] button
    review_btn = page.locator("button:has-text('Review PDF')").first
    expect(review_btn).to_be_visible()
    review_btn.click()

    # 5. Verify PDF review modal opens
    modal = page.locator("#modal-container")
    expect(modal).to_be_visible(timeout=5000)
    expect(modal.locator("iframe")).to_be_visible()
    expect(modal.locator("text=Total Amount")).to_be_visible()

    # 6. Close the modal
    close_btn = modal.locator("button:has-text('Close')")
    close_btn.click()
    expect(modal.locator("iframe")).not_to_be_visible()

    # 7. Click [Receive] button
    receive_btn = page.locator("button:has-text('Receive')").first
    expect(receive_btn).to_be_visible()
    receive_btn.click()

    # 8. Verify the button updates to "Successfully Received"
    expect(page.locator("button:has-text('Successfully Received')").first).to_be_visible(timeout=5000)

    # 9. Search for a non-existent item
    search_input.fill("UnknownCryogenicValve123")
    expect(page.locator("text=No matching quotation found")).to_be_visible(timeout=5000)

    # 10. Click [Request Quotation Manually]
    manual_btn = page.locator("button:has-text('Request Quotation Manually')")
    expect(manual_btn).to_be_visible()
    manual_btn.click()

    # 11. Verify modal appears and submit
    expect(modal.locator("text=Request Quotation Manually")).to_be_visible(timeout=5000)
    page.fill("textarea[name='item_description']", "Special Titanium Cryogenic Valve DN100")
    submit_btn = modal.locator("button:has-text('Submit Demand')")
    submit_btn.click()

    # 12. Verify ticket confirmation
    expect(page.locator("text=Request Submitted Successfully")).to_be_visible(timeout=5000)
    expect(page.locator("text=REQ-")).to_be_visible()

    # Close confirmation modal
    page.locator("#modal-container button:has-text('Close')").click()

    # 13. Navigate to PH Workbench
    page.goto("http://127.0.0.1:8000/ph-portal")
    expect(page.locator("text=Purchasing Hub (PH) Workbench")).to_be_visible()
    expect(page.locator("text=Pending Manual Demands Queue")).to_be_visible()
    expect(page.locator("text=Special Titanium Cryogenic Valve DN100").first).to_be_visible()


def test_e2e_multilingual_search_thai_and_japanese(page: Page):
    # 1. Open homepage
    page.goto("http://127.0.0.1:8000/")
    search_input = page.locator("#search-input")
    expect(search_input).to_be_visible()

    # 2. Search in Thai: "กล่อง" (box) -> Button Box
    search_input.fill("กล่อง")
    expect(page.locator("#search-results table")).to_be_visible(timeout=5000)
    expect(page.locator("text=Button Box Control Unit Project")).to_be_visible()
    expect(page.locator("text=98.0%")).to_be_visible()

    # 3. Search in Japanese Katakana: "ベルト" (belt) -> Bando Belt
    search_input.fill("ベルト")
    expect(page.locator("#search-results table")).to_be_visible(timeout=5000)
    expect(page.locator("text=BANDO CHEMICAL INDUSTRIES")).to_be_visible()

    # 4. Search in Japanese Kanji: "箱" (box) -> Button Box
    search_input.fill("箱")
    expect(page.locator("#search-results table")).to_be_visible(timeout=5000)
    expect(page.locator("text=Button Box Control Unit Project")).to_be_visible()

    # 5. Search by conceptual meaning in Thai: "ภาชนะ" (container/receptacle) -> Button Box
    search_input.fill("ภาชนะ")
    expect(page.locator("#search-results table")).to_be_visible(timeout=5000)
    expect(page.locator("text=Button Box Control Unit Project")).to_be_visible()


def test_e2e_smart_pdf_auto_extraction_for_ph_user(page: Page):
    import os
    # 1. Navigate to PH Portal
    page.goto("http://127.0.0.1:8000/ph-portal")
    expect(page.locator("text=Smart Quotation Ingestion & Auto-Extraction")).to_be_visible()

    # 2. Upload PDF file via file input
    pdf_path = os.path.abspath(os.path.join("quoatation", "26Q13131 (2).pdf"))
    file_input = page.locator("#pdf_file")
    file_input.set_input_files(pdf_path)

    # 3. Verify smart auto-extraction banner and auto-filled values appear
    expect(page.locator("text=Smart Auto-Extraction Complete")).to_be_visible(timeout=8000)
    expect(page.locator("#input_quotation_number")).to_have_value("26Q13131")
    expect(page.locator("#input_vendor_name")).to_have_value(re.compile("IWASE"))
    expect(page.locator("#input_issue_date")).to_have_value("2026-07-31")

    # 4. Click Confirm & Ingest Quotation WITHOUT typing anything!
    submit_btn = page.locator("#submit-btn")
    submit_btn.click()

    # 5. Verify redirected back to /ph-portal and quotation is listed in Active table
    expect(page).to_have_url("http://127.0.0.1:8000/ph-portal")
    expect(page.locator("text=Purchasing Hub (PH) Workbench")).to_be_visible()

    # 6. Verify searchable on homepage
    page.goto("http://127.0.0.1:8000/")
    search_input = page.locator("#search-input")
    search_input.fill("IWASE")
    expect(page.locator("#search-results table")).to_be_visible(timeout=5000)
    expect(page.locator("text=IWASE (Thailand) Co., Ltd.")).to_be_visible()


def test_e2e_bad_path_and_recovery_simulation(page: Page):
    """Simulates real user bad paths, error feedback, and happy path recovery in the browser."""
    # 1. Navigate to PH Portal
    page.goto("http://127.0.0.1:8000/ph-portal")
    expect(page.locator("text=Purchasing Hub (PH) Workbench")).to_be_visible()

    # 2. Check expired quotation renewal bad path (enter past date)
    expired_table = page.locator("text=Expired Commercial Quotations").locator("..")
    renew_date_inputs = page.locator("input[name='new_expiration_date']")
    if renew_date_inputs.count() > 0:
        first_renew_input = renew_date_inputs.first
        first_renew_input.fill("2020-01-01")
        renew_form = first_renew_input.locator("xpath=ancestor::form")
        renew_form.locator("button[type='submit']").click()

        # Should show [ERROR] row or feedback
        expect(page.locator("text=[ERROR] Invalid validity period").first).to_be_visible(timeout=5000)

    # 3. Simulate Happy Path Manual Request & Fulfillment
    page.goto("http://127.0.0.1:8000/")
    page.locator("#search-input").fill("NonExistentRoboticArmFixture")
    expect(page.locator("text=No matching quotation found")).to_be_visible(timeout=5000)

    # Open manual request modal
    page.locator("button:has-text('Request Quotation Manually')").click()
    modal = page.locator("#modal-container")
    expect(modal.locator("text=Request Quotation Manually")).to_be_visible(timeout=5000)

    # Fill demand details
    page.fill("textarea[name='item_description']", "Heavy Duty Ceramic Bearing 50mm")
    page.fill("input[name='part_number']", "HDCB-50")
    page.fill("input[name='target_quantity']", "10")
    modal.locator("button:has-text('Submit Demand')").click()

    # Verify confirmation
    expect(page.locator("text=Request Submitted Successfully")).to_be_visible(timeout=5000)
    match_ticket = page.locator("text=REQ-").first
    expect(match_ticket).to_be_visible()
    ticket_text = match_ticket.inner_text()

    # Close modal
    page.locator("#modal-container button:has-text('Close')").click()

    # Navigate to PH Workbench to fulfill
    page.goto("http://127.0.0.1:8000/ph-portal")
    expect(page.locator("text=Heavy Duty Ceramic Bearing 50mm").first).to_be_visible()

    # Locate the fulfill form for this ticket
    req_row = page.locator("tr:has-text('Heavy Duty Ceramic Bearing 50mm')").first
    expect(req_row).to_be_visible()

    # Bad Path: Fulfill with ghost quotation ID
    req_row.locator("input[name='quotation_id']").fill("QT-GHOST-12345")
    req_row.locator("button:has-text('Fulfill')").click()
    # Toast error notification should appear
    expect(page.locator("#toast-container")).to_be_visible()

    # Happy Path: Fulfill with valid existing quotation ID (e.g. QT-137836)
    req_row.locator("input[name='quotation_id']").fill("QT-137836")
    req_row.locator("button:has-text('Fulfill')").click()

    # Verify ticket transitions to [OK] Closed
    expect(page.locator("text=[OK] Closed").first).to_be_visible(timeout=5000)

