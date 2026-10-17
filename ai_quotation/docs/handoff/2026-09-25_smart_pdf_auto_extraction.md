# Handoff Note - 2026-09-25 (Smart PDF Auto-Extraction for PH Users)

## Summary of Accomplishments
1. **Smart PDF Extraction Engine (Infrastructure & Domain)**:
   - Added `ExtractedQuotationDraft` and `DraftItem` in `src/domain/extracted_quotation_draft.py`.
   - Added `PdfDocumentReader.extract_draft(file_path: str)`:
     - Automatically parses quotation numbers (`26Q13131`, `099-320`, `137836`, `QT0416359`, etc.).
     - Accurately identifies vendor names (while filtering out buyer entities like NMB-Minebea).
     - Extracts vendor 13-digit tax IDs.
     - Detects issue dates with Thai Buddhist Era conversion (`69` -> 2569 BE -> 2026 CE).
     - Detects validity duration terms ("30 days", "90 days", "180 days") and calculates expiration dates.
     - Detects currencies (`THB`, `JPY`, `USD`, `EUR`).
     - Extracts line item tables (item number, description, part numbers / model specifications, quantities, units, unit prices, amounts).
2. **Application & Web Interfaces**:
   - `QuotationApplicationService.extract_draft_from_pdf` provides RBAC-guarded extraction preview.
   - Added `POST /api/quotations/extract-preview` endpoint returning draft JSON for instant client-side preview.
   - Updated `POST /api/quotations/register` to support optional input fields, falling back automatically to the extracted PDF draft when fields are omitted.
3. **Purchasing Hub (PH) UI Experience**:
   - Updated `templates/ph_portal.html`:
     - File selection immediately triggers asynchronous preview extraction.
     - Displays an emerald confirmation card with extracted chips: Quotation #, Vendor, Validity Dates, Items Extracted, Total.
     - Automatically fills all input fields with `[Auto-Extracted]` labels.
     - Updates the submit button to `Confirm & Ingest Quotation (Auto-Filled)`, allowing 1-click submission without typing anything.
4. **Verification Proof (Rule 10 & Rule 16)**:
   - Automated tests: 68/68 tests passing (`uv run pytest tests/`).
   - Playwright E2E: Tested PDF upload in real Chromium browser, verified auto-extraction, verified 1-click submission without manual typing, and verified searchable discovery on homepage (3/3 passing).
   - Live Uvicorn server running on `http://127.0.0.1:8000`.
