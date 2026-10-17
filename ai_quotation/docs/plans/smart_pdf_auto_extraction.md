# Plan: Smart PDF Auto-Extraction for PH User Workflow

## 1. Goal
Minimize or eliminate manual input fields for Purchasing Hub (PH) users by implementing intelligent automatic extraction of quotation metadata and line items directly from uploaded PDF documents.

## 2. Ubiquitous Language & Domain Concepts
- `ExtractedQuotationDraft`: Domain value object representing candidate quotation metadata and line items automatically extracted from a vendor document.
- `SmartPdfExtractor` / `PdfDocumentReader`: Infrastructure component parsing raw PDF streams into structured drafts (vendor, quotation number, dates, currency, tax ID, line items).
- `ValidityPeriod`: Auto-calculating issue and expiration dates based on vendor validity terms (e.g., "30 days", "90 days", or explicit dates with BE-to-CE conversion).

## 3. Phased Implementation Plan
- **Phase 1: Domain & Infrastructure (RED -> GREEN)**:
  - Add `ExtractedQuotationDraft` and structured item draft models.
  - Enhance `PdfDocumentReader` with smart heuristics:
    - Quotation number extraction patterns (QT, QUOTATION, NO., SO, etc.)
    - Vendor detection with entity keywords (Co., Ltd., Corp, Inc., etc.)
    - Multi-format date extraction (DD/MM/YYYY, YYYY-MM-DD, Month DD YYYY, BE year 2569/69 -> 2026)
    - Validity period duration detection ("30 days", "90 days")
    - Line item table extraction (Item number, Description, Part number, Quantity, Unit, Price, Amount)
    - Currency and Tax ID detection
  - Write failing tests in `tests/unit/infrastructure/test_smart_pdf_extraction.py`.
- **Phase 2: Application Layer Service (RED -> GREEN)**:
  - Add `extract_draft_from_pdf(file_path: str, user_role: str) -> ExtractedQuotationDraft` to `QuotationApplicationService`.
  - Add unit and integration tests.
- **Phase 3: Web Interfaces & UI (RED -> GREEN)**:
  - Add `POST /api/quotations/extract-preview` endpoint returning extracted draft as JSON.
  - Upgrade `templates/ph_portal.html` with smart upload zone:
    - Drag-and-drop / file select triggers instant auto-extraction.
    - Shows dynamic preview with `[Auto-Extracted]` indicators.
    - PH user can simply click "Confirm & Ingest" without manual typing!
- **Phase 4: Playwright E2E Verification**:
  - Test real browser file upload in PH portal and verify auto-population of fields and successful ingestion.

## 4. Verification Approach
- 100% test pass on pytest suite.
- Playwright E2E verification on real browser.
