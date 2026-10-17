# Project Audit & Architecture Overview: QuotationFinder

[INFO] This report provides an audit of the repository located at `d:/ProjectQuotation/quotation_search/quotation_search`, detailing **what it does**, **how it works**, and **what assets and deliverables are present**.

---

## 1. What This Project Does

**QuotationFinder** is an industrial procurement search engine, lifecycle tracker, and AI copilot platform. It solves a common manufacturing problem: **procurement teams and engineers lose track of vendor quotation PDFs**, risk buying parts using expired or outdated pricing agreements, or spend unnecessary time re-requesting quotes that already exist.

The system serves two primary roles:

### A. Normal Users (Engineers / Requesters)

- **Instant Hybrid Search**: A Google-style interface to search across commercial quotations using part numbers (e.g. `5V-1400`, `A-61(S)`), manufacturer names (e.g. `Bando`, `Iwase`, `Minebea`), model codes, or technical descriptions.
- **Multilingual & Concept Search**: Supports queries in **English**, **Thai** (e.g. `กล่อง`, `สายพาน`), and **Japanese** (e.g. `箱`, `ボックス`, `ベルト`). It also resolves abstract conceptual queries (hypernyms), such as searching Thai `ภาชนะ` (container/receptacle) to discover physical button boxes or control unit enclosures.
- **In-Browser PDF Review**: Users can open the original vendor PDF inside an interactive modal viewer with highlighted metadata, line items, and validity dates without downloading the file.
- **Claim / Receive Action**: Users can claim or acknowledge an active quotation for a bill of materials (BOM), recording an audit trail while keeping the quotation searchable for others.
- **Manual Quotation Demand**: If a search yields no results, users can open a modal to submit a manual quotation request specifying part description, estimated quantity, and urgency (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **AI Procurement Copilot (RAG)**: Users can ask natural-language questions (e.g., _"Which vendor provides the lowest price for V-belts?"_ or _"มีสินค้าอะไรบ้าง"_). The system synthesizes answers grounded in actual PDF quotes and renders clickable **`[Research]`** and **`[PDF]`** citation rows.

### B. Purchasing Hub (PH) Users (Procurement Officers)

- **Smart PDF Auto-Extraction (Zero-Input Ingestion)**: PH officers drag-and-drop vendor quotation PDFs. The parser automatically extracts the quotation number, vendor name, tax ID, currency, issue date, expiration date (including Thai Buddhist Era `2569 BE` -> `2026 CE` conversions and `30/90/180-day` validity terms), and line-item tables with unit prices.
- **Quotation Lifecycle & Expiration Monitoring**: Automatically marks quotations past their expiration date as `EXPIRED`, hiding them from standard searches to prevent ordering on invalid prices. PH users can execute in-place renewals with a single click.
- **Manual Demand Workbench**: PH users view, manage, and fulfill pending quotation requests raised by engineers once new vendor agreements arrive.

---

## 2. How It Works (System Architecture & Data Flow)

The application follows **Domain-Driven Design (DDD)** organized into four clean layers, completely separating business logic from frameworks and databases:

```
                  +-----------------------------------+
                  |         Interfaces Layer          |
                  |  FastAPI Web App & HTML Templates |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |         Application Layer         |
                  |  QuotationApplicationService      |
                  |  QuotationInquiryService (RAG)    |
                  +-----------------+-----------------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
  +-----------------------------------+   +--------------------+
  |       Infrastructure Layer        |   |    Domain Layer    |
  |  - SqliteQuotationRepository      |   |  - Quotation       |
  |  - MemoryVectorIndex (FastEmbed)  |   |  - ValidityPeriod  |
  |  - MemorySearchCache & Inquiry    |   |  - Multilingual    |
  |  - PdfDocumentReader (PyPDF)      |   |  - ManualRequest   |
  |  - GeminiAnswerGenerator          |   |  - ConfidenceScore |
  +-----------------------------------+   +--------------------+
```

### Key Modules & Components

1. **Domain Layer** (`src/domain/`):
   - [quotation.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/domain/quotation.py): `Quotation` aggregate root managing line items, claims, and status transitions (`ACTIVE`, `EXPIRED`, `SUPERSEDED`, `ARCHIVED`).
   - [validity_period.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/domain/validity_period.py): Enforces business rules (e.g. renewal dates must be strictly in the future; expired quotes cannot be received).
   - [multilingual_lexicon.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/domain/multilingual_lexicon.py): Cross-lingual domain dictionary connecting Thai, Japanese, and English terms with word-boundary tokenization guards.
   - [extracted_quotation_draft.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/domain/extracted_quotation_draft.py): Value object containing auto-extracted PDF draft data.
   - [manual_quotation_request.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/domain/manual_quotation_request.py): Aggregate root tracking engineer requests from `PENDING` to `FULFILLED`.

2. **Application Layer** (`src/application/`):
   - [quotation_service.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/application/quotation_service.py): Coordinates search queries, PDF indexing, draft extraction, claim audits, and quotation renewals.
   - [quotation_inquiry_service.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/application/quotation_inquiry_service.py): Orchestrates conversational RAG queries. Identifies catalog overview intents (e.g. _"มีอะไรบ้าง"_), augments relevant quotation chunks with raw text snippets, and generates structured citation views.

3. **Infrastructure Layer** (`src/infrastructure/`):
   - [sqlite_quotation_repository.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/sqlite_quotation_repository.py): Persists quotations, line items, and claims into SQLite.
   - [vector_index.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/vector_index.py) & [embedding_engine.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/embedding_engine.py): Generates 384-dimensional dense embeddings locally via FastEmbed (ONNX MiniLM) without needing cloud embedding APIs, combining cosine similarity with token frequency boosting.
   - [search_cache.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/search_cache.py) & [inquiry_cache.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/inquiry_cache.py): In-memory caches using SHA-256 keys, reducing repeat AI inquiry latency from ~2200ms to 0.04ms (>50,000x speedup).
   - [pdf_reader.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/pdf_reader.py): Extracts raw text and uses heuristic regular expressions to detect vendor names, tax IDs, issue/expiration dates, and line item tables.
   - [gemini_answer_generator.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/infrastructure/gemini_answer_generator.py): Calls Google Generative Language API (`gemini-2.5-flash`) with prompt grounding using credentials loaded securely from [credentials.ini](file:///d:/ProjectQuotation/quotation_search/quotation_search/credentials.ini).

4. **Interfaces Layer** (`src/interfaces/`):
   - [web_app.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/interfaces/web_app.py): FastAPI application serving REST endpoints, JSON APIs, and server-side Jinja2 templates.
   - [base.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/base.html): Features a native JavaScript event delegation engine that handles live search debouncing, form submissions, and modals offline with zero external CDN dependencies.

---

## 3. What You Have Got in This Project (Inventory of Assets)

The project is fully built, seeded with data, documented, and tested:

### 1. Application Code & Entry Points

- [main.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/main.py): Application entrypoint. Boots FastAPI with automatic database seeding and vector index re-hydration on port `8000`.
- [pyproject.toml](file:///d:/ProjectQuotation/quotation_search/quotation_search/pyproject.toml): Project package configuration with declared dependencies (`fastapi`, `fastembed`, `jinja2`, `playwright`, `pypdf`, `pytest`, `uvicorn`).
- [src/](file:///d:/ProjectQuotation/quotation_search/quotation_search/src): Complete source tree implementing Domain-Driven Design across 21 files.

### 2. Frontend User Interface (`templates/`)

- [search.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/search.html): Primary Google-style search page with live search bar, quick suggestion pills, and the AI Copilot RAG widget.
- [ph_portal.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/ph_portal.html): Purchasing Hub portal with quotation KPI stats, smart drag-and-drop PDF ingestion, expiration renewals, and demand fulfillment queue.
- [base.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/base.html): Common layout containing the navigation header, role indicator, toast notification system, and offline event handler.
- [partials/search_results.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/partials/search_results.html): Dynamic search results table with confidence percentages, line items, and claim buttons.
- [partials/pdf_modal.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/partials/pdf_modal.html): Embedded PDF viewer modal with quotation details.
- [partials/manual_request_modal.html](file:///d:/ProjectQuotation/quotation_search/quotation_search/templates/partials/manual_request_modal.html): Modal form for submitting manual quotation requests.

### 3. Data & Storage

- [quotations.db](file:///d:/ProjectQuotation/quotation_search/quotation_search/quotations.db): SQLite database pre-populated with schema tables (`quotations`, `quotation_items`, `quotation_acknowledgments`, `manual_quotation_requests`).
- [quoatation/](file:///d:/ProjectQuotation/quotation_search/quotation_search/quoatation): 9 real commercial quotation PDF files used for seeding and testing:
  1. `25-334.pdf`
  2. `26DD09113 _ Botton Box Project M-AL6-001B__ (PMC_Minebea Thai) K. Peerapat.pdf`
  3. `26Q13131 (2).pdf`
  4. `416359.pdf`
  5. `69Q-19458.pdf`
  6. `ใบเสนอราคา (1).pdf`
  7. `BANDO (6).pdf`
  8. `QT NO. 137836.pdf`
  9. `Sales_quotation_0021221998.pdf`
- [storage/](file:///d:/ProjectQuotation/quotation_search/quotation_search/storage): Ingestion storage directory where uploaded quotation PDFs are saved.

### 4. Comprehensive Documentation Suite (`docs/`)

- [system_requirements_and_architecture.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/docs/requirements/system_requirements_and_architecture.md): Formal requirements document containing the Ubiquitous Language dictionary, RBAC matrix, UI wireframes, state machine diagrams, sequence diagrams, and SQL schemas.
- [comprehensive_acceptance_criteria.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/docs/requirements/comprehensive_acceptance_criteria.md): Gherkin acceptance criteria covering 8 core functional features and 7 domain invariants.
- [DECISIONS.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/docs/DECISIONS.md): Architectural Decision Records (`D-001` through `D-016`) detailing choices regarding DDD, local ONNX embeddings, in-place renewals, multilingual search, and RAG caching.
- [NOTES.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/docs/NOTES.md): Engineering laboratory notes recording test proofs, benchmarks (e.g. 0.04ms cache hit latency), and Root Cause Analysis (RCA) records.
- [TODO.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/docs/TODO.md): Living task list documenting 32 completed implementation milestones.

### 5. Test Suite (`tests/`)

The repository contains 98 test cases spanning:

- **Unit Tests** (`tests/unit/`): Testing `Quotation`, `ValidityPeriod`, `MultilingualLexicon`, `MemoryVectorIndex`, `PdfDocumentReader`, `MemorySearchCache`, and `QuotationApplicationService`.
- **Integration Tests** (`tests/integration/`): Testing SQLite persistence, multilingual cross-lingual search, Happy/Bad path failure handling, and caching.
- **API Tests** (`tests/interfaces/`): Testing HTTP endpoints, smart PDF auto-extraction preview, and error responses (400, 403, 404).
- **End-to-End Browser Tests** (`tests/e2e/test_playwright_e2e.py`): Automated Playwright browser tests verifying search debounce, modal openings, claim buttons, multilingual inputs, and smart upload workflows.

---

## 4. Operational Notice & Legacy Remnant Report

[Rule 0 & Rule 19 Report]:

1. **Rule File Origin**: [CLAUDE.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/CLAUDE.md) and [GEMINI.md](file:///d:/ProjectQuotation/quotation_search/quotation_search/GEMINI.md) in this directory contain governance rules and command references (such as `CostReductionAutoLoader`, `cli.py`, `services/purposes/`, `62xx_monitoring`, and MSSQL schemas) that were ported from an earlier ETL data pipeline.
2. **Current Actual Architecture**: In this repository, the true application is the **QuotationFinder** web application driven by [main.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/main.py) and [web_app.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/src/interfaces/web_app.py) using SQLite and FastAPI, rather than a TUI CLI daemon.
3. **Environment State**: The machine's Python environment is currently running Python 3.13, and the local host is in an offline network environment where external PyPI package downloads (`https://files.pythonhosted.org`) are blocked.

---

## 5. Summary

You have a **production-structured, Domain-Driven Design (DDD) Quotation Search and Lifecycle Engine** equipped with:

1. High-speed hybrid vector and multilingual keyword search.
2. Smart PDF extraction for zero-input ingestion of vendor quotes.
3. Lifecycle controls preventing the use of expired quotation pricing.
4. An integrated Gemini 2.5 Flash RAG Copilot with sub-millisecond query caching.
5. A comprehensive documentation, test, and requirement specification suite.

Ran command: `uv run --offline python main.py --help`
Ran command: `uv run --python 3.13 --offline python --version`
Ran command: `Get-ChildItem -Path "C:\Users\bpt9867\AppData\Local" -Recurse -Filter "python.exe" -Depth 4 -ErrorAction SilentlyContinue | Select-Object FullName`
Ran command: `uv python list`
Ran command: `Get-ChildItem -Path "C:\Users\bpt9867" -Recurse -Filter "fastapi*" -Depth 4 -ErrorAction SilentlyContinue | Select-Object FullName`
Viewed credentials.ini:1-4
Viewed .env:1-3
Ran command: `uv python find 3.13`

# User & Operation Guide: QuotationFinder

[INFO] This guide covers how to set up, launch, and operate the QuotationFinder search and procurement lifecycle engine.

---

## 1. Quick Start: How to Launch the Application

### Step 1: Install Dependencies

The application requires Python 3.12 or higher. Dependencies are managed via `uv` or `pip`:

```powershell
# Using uv (recommended)
uv sync

# Or using standard pip
python -m pip install -e .
```

> [!NOTE]
> If working within an isolated corporate network or behind an HTTP proxy, ensure your proxy is set before installing:
>
> ```powershell
> $env:HTTP_PROXY = "http://proxy.yourcompany.com:8080"
> $env:HTTPS_PROXY = "http://proxy.yourcompany.com:8080"
> uv sync
> ```

### Step 2: Start the Web Server

Launch the server using [main.py](file:///d:/ProjectQuotation/quotation_search/quotation_search/main.py):

```powershell
uv run python main.py
```

_(Or directly via python: `python main.py` or `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`)_

On startup, the system will:

1. Initialize the SQLite schema in [quotations.db](file:///d:/ProjectQuotation/quotation_search/quotation_search/quotations.db).
2. Auto-seed 9 commercial vendor quotation PDFs from [quoatation/](file:///d:/ProjectQuotation/quotation_search/quotation_search/quoatation) if the database is empty.
3. Re-hydrate the local in-memory vector index with 384-dimensional dense embeddings.
4. Listen on `http://localhost:8000`.

---

## 2. Engineer / Requester Workflow (Normal User)

Open your browser and navigate to:
**`http://localhost:8000`** (or `http://localhost:8000/search`)

### A. Searching for Quotations

1. **Keyword & Part Number Search**: Type any part number, brand, or model into the central search bar:
   - Examples: `5V-1400`, `Bando V-Belt`, `A-61(S)`, `Botton Box Project M-AL6-001B`.
   - Search results update dynamically with a 250ms debounce.
2. **Multilingual Search (Thai & Japanese)**:
   - Thai: `กล่อง` (box), `สายพาน` (belt).
   - Japanese: `箱` / `ボックス` (box), `ベルト` (belt), `見積書` (quotation).
3. **Conceptual / Meaning-Based Search**:
   - Search by category or function without knowing the exact model name. For example, typing Thai `ภาชนะ` (container/enclosure) discovers control button boxes.

### B. In-Browser PDF Review

1. In the search results table, click the **`[Review PDF]`** button on any quotation row.
2. An interactive modal opens displaying:
   - Vendor name, quotation number, currency, and validity dates.
   - Full line-item breakdown with unit prices.
   - Embedded live PDF document viewer.
3. Click **`[Close]`** or outside the modal backdrop to return to the search view.

### C. Claim / Receive Quotation for BOM

- If a quotation matches your engineering design or project requirements, click **`[Receive]`**.
- This records an audit timestamp and marks the quotation as claimed for your project, while leaving it visible for others in the organization.

### D. Submitting a Manual Quotation Request

If a part is not yet covered by an existing vendor quote:

1. Click the **`[Request Quotation Manually]`** button (or the link in the "No matching quotation found" banner).
2. Complete the modal form:
   - **Item Description**: Part specifications or commercial description.
   - **Required Quantity & Unit**: e.g., `50 PCS`.
   - **Urgency Level**: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
3. Click **`[Submit Request]`**. The demand is immediately routed to the Purchasing Hub workbench.

---

## 3. Purchasing Hub (PH) Workflow

Navigate to the Purchasing Hub portal by clicking the top navigation link or visiting:
**`http://localhost:8000/ph-portal`**

### A. Dashboard Overview

The top KPI cards report real-time procurement health:

- **Active Quotations**: Count of usable, valid vendor agreements.
- **Expired Quotations**: Count of past-due agreements requiring renewal.
- **Pending Demands**: Count of outstanding requests submitted by engineers.

### B. Smart PDF Quotation Ingestion (Zero-Input Mode)

1. In the **Smart Quotation Ingestion** section, click or drag a new vendor quotation PDF into the drop zone.
2. The background engine parses the PDF and detects:
   - Quotation number (e.g. `QT-137836`, `26Q13131`).
   - Vendor name (differentiating supplier from buyer).
   - Issue date & expiration date (automatically converting Thai Buddhist Era years like `2569 BE` -> `2026 CE` and calculating 30/90/180-day validity terms).
   - Currency (`THB`, `USD`, `JPY`).
   - Line items with part numbers, quantities, units, and unit prices.
3. An emerald banner appears showing the auto-extracted values and pre-fills the form.
4. Review the detected fields (edit any field if necessary) and click **`[Confirm & Ingest]`**. The quotation is instantly indexed and searchable.

### C. Quotation Expiration & Renewal

1. Scroll down to the **Quotation Lifecycle Management** table.
2. Filter between `ACTIVE` and `EXPIRED` status tabs.
3. When a vendor agrees to extend pricing on an expired quotation:
   - Enter a new expiration date in the input field (must be strictly in the future).
   - Click **`[Renew Agreement]`**.
   - The quotation immediately transitions back to `ACTIVE` and re-enters the search catalog.

### D. Fulfilling Engineer Quotation Demands

1. Scroll to the **Pending Quotation Demands** section.
2. Review the parts requested by engineers along with their urgency tags.
3. Once you have uploaded the matching vendor quotation:
   - Enter the generated `Quotation ID` into the fulfillment field.
   - Click **`[Fulfill]`**.
   - The demand status changes to `FULFILLED` and the requesting engineer can find the quotation in search.

---

## 4. AI Procurement Copilot (RAG) & Citation Workflow

Located directly below the primary search bar on `http://localhost:8000`:

1. **Ask Natural Language Questions**:
   - General overview: _"มีสินค้าอะไรบ้าง"_ or _"Give me an overview of all active quotations"_
   - Price comparisons: _"Which vendor offers the best price for industrial transmission V-belts?"_
   - Technical specifications: _"สายพานนี้เป็นเเบบไหน"_ or _"What are the dimensions and specs for part A-61(S)?"_
2. **Clickable Interactive Citation Rows**:
   Below the synthesized answer, the assistant displays citation cards for every source quotation:
   - **`[Research]`**: Automatically inserts the quotation number or part name into the main search box and triggers an instant search.
   - **`[PDF]`**: Immediately opens the embedded vendor PDF viewer for inspection.
3. **High-Speed Cache**:
   - Initial queries take ~2 seconds (local retrieval + Gemini 2.5 Flash API).
   - Repeat questions are served from the SHA-256 in-memory cache in **0.04 ms** (over 50,000x faster) with an on-screen `⚡ Cached` badge.

---

## 5. Running Automated Verification & Tests

To execute the test suite (98 automated tests):

```powershell
# Run all unit, integration, and API tests
uv run pytest

# Run a specific test suite
uv run pytest tests/unit/domain/
uv run pytest tests/integration/test_simulation_happy_and_bad_paths.py -v

# Run Playwright end-to-end browser tests (headless Chromium)
uv run pytest tests/e2e/test_playwright_e2e.py -v
```

---

## 6. Configuration & Environment Reference

| File                                                                                             | Purpose                              | Default Settings                                                     |
| ------------------------------------------------------------------------------------------------ | ------------------------------------ | -------------------------------------------------------------------- |
| [credentials.ini](file:///d:/ProjectQuotation/quotation_search/quotation_search/credentials.ini) | Gemini AI API credentials            | Model: `gemini-2.5-flash`                                            |
| [.env](file:///d:/ProjectQuotation/quotation_search/quotation_search/.env)                       | Fallback environment variables       | `GEMINI_API_KEY`, `GEMINI_MODEL`                                     |
| [pyproject.toml](file:///d:/ProjectQuotation/quotation_search/quotation_search/pyproject.toml)   | Python dependencies & pytest options | `requires-python = ">=3.12"`                                         |
| [quotations.db](file:///d:/ProjectQuotation/quotation_search/quotation_search/quotations.db)     | SQLite database                      | Schema: `quotations`, `quotation_items`, `manual_quotation_requests` |
| [storage/](file:///d:/ProjectQuotation/quotation_search/quotation_search/storage)                | Uploaded quotation PDF repository    | Preserves uploaded vendor documents                                  |
