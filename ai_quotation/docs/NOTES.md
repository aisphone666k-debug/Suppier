# Engineering Notes (Rule 4)

## 2026-09-25: Repository Exploration & Initial Specifications (DISCOVERY State)

### Workspace Inspection
- Inspected repository root at `C:\Users\bptk212\Desktop\quotation_search`.
- Discovered 9 sample commercial quotation PDF files in `quoatation/`:
  - `25-334.pdf` (1.18 MB)
  - `26DD09113 _ Botton Box Project M-AL6-001B__ (PMC_Minebea Thai) K. Peerapat.pdf` (193 KB)
  - `26Q13131 (2).pdf` (116 KB)
  - `416359.pdf` (33 KB)
  - `69Q-19458.pdf` (254 KB)
  - `ใบเสนอราคา (1).pdf` (73 KB)
  - `BANDO (6).pdf` (140 KB)
  - `QT NO. 137836.pdf` (55 KB)
  - `Sales_quotation_0021221998.pdf` (32 KB)
- Installed runtime environment: Python 3.13.14, uv 0.9.28.
- Observed that `docs/` and git repository were not yet initialized. Initialized documentation architecture under `docs/`.

### Architecture & Specification Deliverables
- Created comprehensive System Requirements, Architecture, and UI Wireframes document:
  `docs/requirements/system_requirements_and_architecture.md`
  - Complete Ubiquitous Language dictionary (no banned terms).
  - RBAC permission matrix for Normal User and PH User.
  - UI layouts for all 6 pages/views (Google-style search, PDF review modal, Manual Request modal, PH Dashboard, Ingestion Portal, Manual Requests Workbench).
  - Mermaid state machine diagrams: Quotation Lifecycle, Manual Demand Lifecycle, Search Cache Lifecycle.
  - Mermaid sequence diagrams: Semantic Search & Receipt, Expiry Detection & Renewal, Manual Demand Fulfillment.
  - Relational SQL schema and vector indexing specification.
- Created standalone Comprehensive Acceptance Criteria document:
  `docs/requirements/comprehensive_acceptance_criteria.md`
  - 8 core features with exhaustive Gherkin scenarios (Given-When-Then).
  - 7 domain invariants mapped.
  - Resilience, fail-fast error handling, and edge cases.

### Confirmed Architectural Decisions (D-005 through D-008)
- Local FastEmbed (ONNX) selected for zero-API-key CPU embedding.
- FastAPI + Jinja2 + HTMX selected for fast server-driven hypermedia interface.
- Quotation Receive action records user claim/acknowledgment audit while remaining visible.
- Quotation Renewal operates in-place updating expiration date to future and reactivating status.

### Troubleshooting RCA (Rule 20.1): Search for "bando" and "BELT"
1. **WHAT**: Initial query for "bando" and "BELT" on the running server returned 0 results.
2. **WHERE**: `src/interfaces/web_app.py`, `src/application/quotation_service.py`, `src/infrastructure/vector_index.py`.
3. **WHEN**: When server restarted with pre-existing `quotations.db`.
4. **WHY**: In-memory vector store was not re-hydrated on server startup when SQLite database was already present, and token indexing stored full phrase strings rather than individual words.
5. **ACTIONS TAKEN**:
   - Implemented `reindex_all()` in `QuotationApplicationService` and added automatic startup sync in `create_app`.
   - Updated `MemoryVectorIndex.add` to extract and index individual words (e.g. `bando`, `belt`, `5v-1400`, `a-61`) into `_token_index`.
   - Refined PDF reader heuristics to extract line items from `BANDO (6).pdf`.
6. **PROOF**: Executed live HTTP search tests; queries for "bando" and "BELT" both return `BANDO CHEMICAL INDUSTRIES (THAILAND) LTD.` as #1 match with 98.0% confidence score.

### Playwright E2E Browser Verification (Rule 16)
- Installed Playwright and automated headless Chromium browser testing (`tests/e2e/test_playwright_e2e.py`).
- Root cause for click issue: Templates originally relied on external `unpkg.com` CDN for HTMX, which failed to resolve in an intranet environment. Furthermore, `pdf_modal.html` used an invalid Jinja2 filter `split`.
- Resolved by:
  1. Adding a native zero-dependency JavaScript event delegation engine in `templates/base.html` that handles all clicks, live search debounce, modal opening, and form submits with 100% offline reliability.
  2. Passing `pdf_filename` directly in the modal context, eliminating the broken Jinja2 filter.
  3. Setting `min_confidence = 0.65` to cleanly separate relevant semantic results from background noise.
- Automated Playwright E2E test verified:
  - Typing "bando" in search bar and seeing live results table.
  - Clicking `[Review PDF]` and seeing the embedded PDF modal open with iframe and metadata.
  - Clicking `[Close]` and seeing the modal disappear.
  - Clicking `[Receive]` and seeing the button update to "Successfully Received".
  - Searching unknown item and seeing "No matching quotation found" banner.
  - Clicking `[Request Quotation Manually]` and submitting a new demand.
  - Opening `/ph-portal` and seeing the newly submitted demand in the pending queue.
- Total suite status: **50/50 tests passing** in 11.95s.

### Multilingual Search: Thai and Japanese Discovery (Rule 10 & Rule 20.1)
1. **WHAT**: User requested support for searching items in Thai (e.g. `กล่อง` [box], `สายพาน` [belt]) and Japanese (e.g. `箱` / `ボックス` [box], `ベルト` [belt], `見積書` [quotation]).
2. **ROOT CAUSE OF DEFECT (RCA)**:
   - Initial implementation of `MultilingualLexicon.expand_terms` used bidirectional substring matching: `if key in normalized or normalized in key`.
   - When indexing parts such as `A-61(S)`, the isolated character `"s"` triggered substring match against `"boxes"`, causing all box synonyms (including Japanese Kanji `箱`) to be incorrectly associated with Bando belts.
   - Searching `箱` then returned both Button Box and Bando Belt at equal 0.98 confidence score, causing a tie-breaking misordering.
3. **ACTIONS TAKEN**:
   - Built domain model `MultilingualLexicon` (`src/domain/multilingual_lexicon.py`) mapping semantic clusters across English, Thai, and Japanese.
   - Refined `expand_terms` to enforce word-boundary regex containment for ASCII terms (preventing single characters or letter fragments like `"s"` or `"con"` from triggering expansions) while correctly preserving single Kanji characters (`箱`, `弁`) and Thai compound tokens (`กล่องควบคุม`).
   - Integrated `extract_unicode_tokens` supporting Latin, Thai (`U+0E00-U+0E7F`), and Japanese Kanji/Hiragana/Katakana (`U+4E00-U+9FFF`, `U+3040-U+30FF`).
   - Added unit tests (`test_multilingual_lexicon.py`) and integration tests (`test_multilingual_search.py`).
   - Added automated Playwright E2E browser test (`test_e2e_multilingual_search_thai_and_japanese`) verifying real browser search queries in Thai (`กล่อง`) and Japanese (`ベルト`, `箱`).
4. **PROOF & VERIFICATION**:
   - 100% test pass rate across 61 tests (`uv run pytest tests/`).
   - Playwright E2E passed in headless Chromium (2/2 passing in 3.22s).

### Smart PDF Auto-Extraction for PH Users (Rule 10 & Rule 16)
1. **WHAT**: User requested minimizing manual input fields for Purchasing Hub (PH) users by implementing intelligent automatic extraction of quotation numbers, vendor name, issue date, expiration date, tax ID, currency, and line items directly from uploaded PDF documents.
2. **DOMAIN MODEL & INFRASTRUCTURE**:
   - Created `ExtractedQuotationDraft` and `DraftItem` domain value objects in `src/domain/extracted_quotation_draft.py`.
   - Enhanced `PdfDocumentReader.extract_draft()`:
     - Detects quotation numbers using explicit document prefix patterns (e.g., `Quotation:`, `No. :`, `QT`, `SO`, `26DD`).
     - Detects vendor name while filtering out buyer names (e.g., `NMB-MINEBEA THAI`).
     - Detects dates with multi-format parsing (DD/MM/YYYY, Month DD, YYYY) and automatic Thai Buddhist Era conversion (`69` -> 2569 BE -> 2026 CE).
     - Extracts validity terms ("30 days", "90 days", "180 days") to accurately project expiration dates.
     - Parses line-item tables capturing item number, description, part numbers (including `Spec:` or `Model` subtitles), quantities, units, and unit prices.
3. **APPLICATION & INTERFACES**:
   - `QuotationApplicationService.extract_draft_from_pdf` provides RBAC-protected draft preview.
   - Endpoint `POST /api/quotations/extract-preview` returns structured JSON to the client.
   - Endpoint `POST /api/quotations/register` accepts empty/partial fields and falls back automatically to the extracted draft.
   - Frontend in `templates/ph_portal.html` listens to PDF file selection, performs instant background analysis, displays an emerald confirmation banner with auto-extracted chips, and pre-populates all form inputs with `[Auto-Extracted]` indicators.
4. **PROOF & VERIFICATION**:
   - Unit tests: `tests/unit/infrastructure/test_smart_pdf_extraction.py` (3/3 passing).
   - Application tests: `test_extract_draft_from_pdf` in `tests/unit/application/test_quotation_application_service.py` (passing).
   - Web API tests: `test_smart_extract_preview_endpoint` and `test_smart_register_with_auto_extracted_fields` in `tests/interfaces/test_web_api.py` (passing).
   - Playwright E2E: `test_e2e_smart_pdf_auto_extraction_for_ph_user` uploaded a real PDF, auto-extracted IWASE metadata, submitted with zero typing, and verified searchable discovery (3/3 passing).
   - Total test suite: **68/68 passing (100% green bar)**.

### Semantic Meaning-Based Discovery (Hypernyms, Ontologies & Aligned Embeddings)
1. **WHAT**: User requested finding items by conceptual meaning rather than literal text (e.g. searching Thai `ภาชนะ` [container/receptacle] discovering "Button Box" [กล่อง / ตู้ควบคุม / enclosure]).
2. **COMPARISON OF METHODS**:
   - **Method A: Pure Embedding Search (Unsupervised Vectors)**:
     - Embedding models like `bge-small-en-v1.5` fail on non-English tokens (`ภาชนะ` produces near-zero or random cosine similarity).
     - Multilingual models (like `paraphrase-multilingual-MiniLM-L12-v2`) place cross-lingual terms in a shared space, but short single-word abstract queries (`ภาชนะ`) vs specific technical product names (`Button Box Control Unit Project M-AL6-001B`) yield modest cosine similarity (~0.14 - 0.31), often falling below confidence thresholds.
   - **Method B: Domain Concept Ontologies (Hierarchical Hypernym-Hyponym Thesaurus)**:
     - Maps abstract procurement concepts (e.g. `ภาชนะ` -> container / receptacle / enclosure) to concrete manufacturing components (`box`, `button box`, `control box`, `casing`, `housing`, `กล่อง`, `ตู้`, `箱`, `容器`).
     - Highly deterministic, fast, zero GPU/API overhead, explainable confidence score.
   - **Method C: Hybrid Lexical-Semantic Fusion (Selected & Implemented)**:
     - Dense multilingual vectors capture continuous semantic context.
     - `MultilingualLexicon` captures exact domain ontological equivalence, connecting Thai hypernyms (`ภาชนะ`, `ที่บรรจุ`, `กล่องบรรจุ`) to English/Japanese physical equipment (`box`, `enclosure`, `container`, `箱`, `容器`).
3. **PROOF & VERIFICATION**:
   - Unit test: `test_lexicon_expands_thai_container_panchana_to_box` verifies `ภาชนะ` expands to `box`, `container`, `กล่อง`, `箱`.
   - Integration test: `test_search_thai_container_finds_button_box` confirms query `ภาชนะ` returns `Button Box` with 0.98 confidence.
   - Playwright E2E: `test_e2e_multilingual_search_thai_and_japanese` verifies typing `ภาชนะ` in live browser discovers Button Box.
   - Test suite status: **70/70 passing (100% green bar)**.

---

### [2026-09-25] UI Review, Happy & Bad Path Simulation, and RAG Architecture

1. **Happy Path vs. Bad Path Simulation Results**:
   - **Bad Paths Validated**:
     - Attempting to receive an expired quotation -> returns HTTP 400 Bad Request with inline status badge `[ERROR] Quotation has expired and cannot be received`.
     - Attempting to receive non-existent quotation -> returns HTTP 404 Not Found.
     - Renewing quotation with past/current date -> returns HTTP 400 Bad Request with inline table error row `[ERROR] Invalid validity period: renewal date must be strictly in the future`.
     - Renewing with invalid date string -> returns HTTP 400 Bad Request.
     - Normal user attempting renewal or registration -> returns HTTP 403 Forbidden.
     - Ingesting corrupt or non-PDF payload -> returns HTTP 400 with `Invalid or corrupt PDF document`.
     - Submitting manual demand with empty description or non-positive quantity -> returns HTTP 400 Bad Request with domain validation error.
     - Fulfilling manual demand with non-existent quotation ID -> returns HTTP 404 Not Found, preserves the table row intact, and emits an error toast.
   - **DOM Preservation Guard**:
     - In `templates/base.html`, guarded event delegation DOM swapping so that non-HTML error payloads (such as JSON `{"detail": ...}`) are never injected into table rows or containers. This prevents client DOM destruction during failed operations.
   - **Test Suite Status**:
     - 11 new integration tests in `tests/integration/test_simulation_happy_and_bad_paths.py`.
     - 1 new browser-driven Happy/Bad path recovery simulation in `tests/e2e/test_playwright_e2e.py`.
     - Full suite status: **82/82 passing (100% green bar)**.

2. **RAG (Retrieval-Augmented Generation) Capability**:
   - **Can we use RAG?**: YES, absolutely!
   - In our current system architecture, the **Retrieval (R)** half is already built and fully operational:
     - Vector Index (`MemoryVectorIndex` with 384-dimensional dense embeddings via `FastEmbedEngine`).
     - Multilingual Lexical-Semantic Expander (`MultilingualLexicon` handling English, Thai, Japanese).
     - Hybrid reranker combining cosine similarity, token match boosting, and validity penalties.
   - **How RAG can be applied**:
     - **Natural Language Procurement Copilot**: User asks questions like: *"Which vendor has the best price for industrial transmission belts?", "Compare IWASE and BANDO terms", "What is the delivery condition for quotation 137836?"*
     - **Augmented Generation**: The top-k matching quotation chunks (items, currency, unit prices, validity dates, raw extracted text) are retrieved and injected into an LLM prompt as ground truth context.
     - **Hallucination-Proof Answers**: The model answers citing exact Quotation IDs, Page numbers, and unit prices from verified repository documents.

3. **Live Gemini 2.5 Flash RAG Verification**:
   - Model: `gemini-2.5-flash` via Google Generative Language REST API (`v1beta`).
   - Secure Key Storage: Loaded from gitignored `credentials.ini`.
   - Priority Order: `credentials.ini` prioritizes over system environment variables.
   - Tested Live Output (English):
     > *"The price of the Bando Industrial Transmission V-Belt (Part: A-61(S)) is 1500.0 THB. This is from BANDO CHEMICAL INDUSTRIES (THAILAND) LTD., Quotation No: 2026, and is currently ACTIVE."*
   - Tested Live Output (Thai):
     > *"DooDee Technology Co.,Ltd. (Quotation No: 099-320) เสนอราคาสำหรับ Button Box Control Unit Project M-AL6-001B ที่ 1500.0 THB โดยสถานะใบเสนอราคาเป็น ACTIVE"*
   - Full Suite Pass Rate: **88/88 tests passing (100% green bar)**.

4. **Inquiry Caching & Self-Performance Telemetry (Rule 1 & 10)**:
   - **Infrastructure**: Implemented `MemoryInquiryCache` with SHA-256 composite keys `hash(clean_role + ":" + clean_query)`, 30-minute TTL, and thread-safe store.
   - **Performance Benchmark**:
     - Cold Call (Cache Miss): **2245.83ms** (Retrieval + Gemini 2.5 Flash API).
     - Warm Call (Cache Hit): **0.04ms** (Instant in-memory lookup).
     - Speedup: **>50,000x latency reduction** on repeated queries with zero external network traffic.
   - **Structured Logging**: `quotation_finder.rag` outputs structured logs including `retrieval_ms`, `generation_ms`, and `total_ms`.
   - **UI Telemetry**: Badges dynamically render `⚡ Cached (0.04ms)` or `Gemini 2.5 Flash (2245.83ms)` giving human users full execution transparency.
   - **Suite Pass Rate**: **95/95 tests passing (100% green bar)**.


5. **Agentic Conversational & Specification Inquiry Capabilities (2026-09-25)**:
   - **User Query Problem**:
     - Users ask broad overview questions in natural Thai ("มีอะไรบ้าง", "มีอะบ้าง", "มีสินค้าอะไร") which previously scored below the 0.65 threshold in vector cosine similarity because quotation PDFs don't contain those literal words.
     - Users ask deep technical specification questions ("สายพานนี้เป็นเเบบไหน") requiring technical context from the raw extracted PDF rather than just high-level line item names.
   - **Architectural Solution**:
     - **Overview Intent Detection**: Added `_is_catalog_overview_intent` in `QuotationInquiryService` (Application layer) capturing Thai overview keywords (`มีอะไรบ้าง`, `มีอะบ้าง`, `มีสินค้าอะไร`, `ขอรายการทั้งหมด`, etc.) and English equivalents (`what do you have`, `overview`, `catalog`).
     - **Catalog Context Compilation**: Overview intent retrieves all active quotations directly from `quotation_repository.find_all()`.
     - **Raw Technical Snippet Augmentation**: Extended `QuotationChunkContext` with `raw_text_snippet` populated with `q.raw_text[:1200]`.
     - **Agentic Procurement Consultation Guidelines**: Updated Gemini 2.5 Flash system prompt instructing the model to act as an industrial procurement consultant, grouping catalog overviews with bullet points, and breaking down mechanical belt specifications (cross-section profiles, trapezoidal belts, intended industrial use).
   - **Live Verification**:
     - Query `มีอะไรบ้าง`: Returns structured Thai summary of active quotations and vendors (`ขณะนี้มีใบเสนอราคาที่ใช้งานอยู่ดังต่อไปนี้...`).
     - Query `สายพานนี้เป็นเเบบไหน`: Returns detailed technical specification breakdown (`สายพานแบบสี่เหลี่ยมคางหมู (Trapezoidal belt) ผู้ขาย: NMB-MINEBEA...`).
     - Repeat inquiries hit cache in 0.03ms.
   - **Suite Pass Rate**: **97/97 tests passing (100% green bar)**.


6. **Interactive Citation Lines & Search Engine Research Integration (2026-09-25)**:
   - **User Request**: "make it agentic can formating a info into a line for make a user click or resesach like a tradinion search engine".
   - **Architectural Solution**:
     - **Domain/Application DTO**: Created `QuotationCitationView` capturing `quotation_id`, `quotation_number`, `vendor_name`, `items_summary`, `price_summary`, `status`, and `search_query`.
     - **Inquiry Result View**: Added `citations: tuple[QuotationCitationView, ...] = ()` to `InquiryResultView`.
     - **Cache Synchronization**: Extended `MemoryInquiryCache` to store and retrieve `citations` along with `answer`, ensuring instantaneous 0.03ms cached responses retain the full interactive UI capabilities.
     - **UI Interactive Lines**: Rendered each referenced quotation below the AI summary as an interactive line card featuring:
       1. `[Research]`: Calls `setQuery('{search_query}')` to instantly feed the part/quotation into the primary search bar and fire an interactive search just like a traditional search engine.
       2. `[PDF]`: Triggers `hx-get="/pdf-modal/{quotation_id}"` to open the quotation document directly in the modal viewer.
       3. Status Badges (`ACTIVE`, `EXPIRED`) and price breakdown.
   - **Test Proof**:
     - Author test `test_agentic_inquiry_generates_interactive_clickable_citation_lines` in `tests/unit/application/test_agentic_inquiry_capabilities.py`.
     - Added UI integration assertions in `tests/interfaces/test_web_api.py`.
     - Test Suite: **98/98 passing (100% green bar)**.


7. **Main.py Startup Diagnostics and Web Server Lifecycle (2026-09-30)**:
   - **User Symptom**: Running uv run python main.py appeared to hang or get stuck, leading to suspicion of hardware issues.
   - **Root Cause Analysis (RCA)**:
     1. Cold start DLL load: FastEmbed requires onnxruntime (onnxruntime.dll [18.4 MB] and onnxruntime_pybind11_state.pyd [19.1 MB]). On Windows with Defender scanning, importing these native binaries takes ~24.8s.
     2. Silent initialization: create_app() was previously executed at module scope before any stdout output, giving the illusion of a frozen process.
     3. Long-running process: main.py is a Uvicorn HTTP server listening continuously on port 8000; it intentionally does not exit back to the terminal prompt.
   - **Remediation**:
     - Added immediate unbuffered flush=True status logs in main.py informing user of model loading and web server availability at http://localhost:8000.
   - **Verification**:
     - Verified main.py initialization and 86/86 unit and integration tests passing (uv run pytest tests/unit tests/integration).
