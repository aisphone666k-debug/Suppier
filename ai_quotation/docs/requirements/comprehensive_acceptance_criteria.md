# Comprehensive Acceptance Criteria Specification

Document Version: 1.0.0  
Status: APPROVED (STATE: DISCOVERY)  
Author: Antigravity Autonomous Agent  
Repository: quotation_search  
Related Specification: [system_requirements_and_architecture.md](file:///C:/Users/bptk212/Desktop/quotation_search/docs/requirements/system_requirements_and_architecture.md)

---

## 1. Overview and Standards

This document establishes the exhaustive, binding Acceptance Criteria (AC) for the Quotation Discovery and Lifecycle Engine. Every criterion is written using the Gherkin specification standard (`Given-When-Then-And`) and mapped directly to domain invariants, validation rules, and regression tests.

### Invariant Catalog Reference
- **INV-01 (Validity Range)**: `expiration_date` must be greater than or equal to `issue_date`.
- **INV-02 (Active Eligibility)**: A quotation is eligible for receipt if and only if `current_date <= expiration_date` and `status == 'ACTIVE'`.
- **INV-03 (Auto-Expiration)**: When `current_date > expiration_date`, a quotation must be treated as `EXPIRED` and hidden from standard normal user purchase flows.
- **INV-04 (Renewal Prerequisite)**: Only an authenticated PH User can execute a renewal, and the new `expiration_date` must be strictly greater than `current_date`.
- **INV-05 (Confidence Range)**: Confidence scores must evaluate to a real number strictly bounded within `[0.000, 1.000]`.
- **INV-06 (Deterministic Cache)**: Cache returns must be functionally identical to fresh query executions for identical index states.
- **INV-07 (Role Isolation)**: Any action attempted outside a user's role must fail fast loudly with an authorization rejection.

---

## 2. Feature-by-Feature Acceptance Criteria

### Feature 1: Semantic & Keyword Quotation Discovery (Google-Like Search)

#### AC-01.01: Semantic Match with High Confidence
```gherkin
Scenario: Normal User enters natural language description matching technical intent
  Given the vector index contains a quotation "QT-137836" with line items "Bando V-Belt Power Ace 5V-1400"
  And the quotation "QT-137836" is in status "ACTIVE" with expiration date "2026-12-31"
  When a Normal User searches for "heavy duty industrial transmission rubber belt"
  Then the system computes the query embedding vector
  And executes a cosine similarity search against the vector repository
  And returns "QT-137836" in the results table
  And displays a Confidence Score greater than or equal to 0.750 (75.0%)
  And displays the Vendor Name, Matched Line Items, and Expiration Date
```

#### AC-01.02: Exact Keyword or Part Number Match
```gherkin
Scenario: Normal User searches by exact part number
  Given quotation "QT-69Q19458" exists containing part number "M-AL6-001B"
  When the user searches for "M-AL6-001B"
  Then the system identifies an exact token match
  And returns "QT-69Q19458" as the top ranked result with Confidence Score >= 0.950 (95.0%)
```

#### AC-01.03: Zero Matches or Sub-Threshold Confidence
```gherkin
Scenario: User searches for an item not present in the repository
  Given no quotation in the system matches "Submarine Nuclear Propulsion Reactor"
  When the user submits "Submarine Nuclear Propulsion Reactor"
  Then the system finds no quotation with Confidence Score >= 0.350
  And renders an empty results notification: "No matching quotation found"
  And displays a prominent Call-to-Action button "[Request Quotation Manually]"
```

---

### Feature 2: Dual-Layer Key-Value Caching and Invalidation

#### AC-02.01: Query Cache Hit Performance
```gherkin
Scenario: Repeated identical search query utilizes Key-Value Cache
  Given a user previously searched for "pneumatic air cylinder" generating cache key "hash('pneumatic air cylinder')"
  When another user searches for "pneumatic air cylinder" within the cache TTL
  Then the query service resolves results directly from the Key-Value Cache
  And skips embedding generation and vector database distance computation
  And returns identical ranked results and confidence scores
  And logs cache status "[OK] CACHE_HIT"
```

#### AC-02.02: Cache Invalidation on New Quotation Ingestion
```gherkin
Scenario: Ingestion of a new quotation purges stale query cache
  Given the Key-Value Cache holds cached results for "Bando transmission belt"
  When a PH User registers a new quotation containing "Bando High Performance Belt"
  Then the system triggers a cache invalidation event
  And subsequent searches for "Bando transmission belt" produce a cache miss and re-index results
```

---

### Feature 3: Inline High-Fidelity PDF Review Modal

#### AC-03.01: PDF Review Modal Rendering
```gherkin
Scenario: User opens PDF preview from search results
  Given quotation "QT-26DD09113" is displayed in the search results table
  And the associated PDF file exists in storage at "storage/pdf/26DD09113.pdf"
  When the user clicks the "[Review PDF]" button
  Then an inline split-screen modal opens displaying the PDF in the left viewport
  And displays the verified metadata (Vendor, Tax ID, Total Amount, Expiration) in the right panel
  And renders a "[Receive]" button if the user is a Normal User and the quotation is ACTIVE
```

#### AC-03.02: Missing PDF File Handling (Fail-Fast Rule 13)
```gherkin
Scenario: Quotation record references a missing PDF file
  Given quotation "QT-CORRUPTED" exists in the database
  But the underlying file "storage/pdf/missing.pdf" does not exist on disk
  When the user clicks "[Review PDF]"
  Then the system fails fast loudly with an error "FileNotFoundError: Quotation document not found on storage"
  And logs the failure with status "[ERROR]"
  And does NOT display an empty or blank fallback modal
```

---

### Feature 4: Normal User Quotation Acknowledgment ("Receive")

#### AC-04.01: Successful Quotation Claim
```gherkin
Scenario: Normal User receives an active quotation
  Given quotation "QT-137836" is in status "ACTIVE" with expiration date "2026-12-31"
  When a Normal User clicks "[Receive]" on "QT-137836"
  Then the system records a `QuotationAcknowledgedEvent`
  And saves an audit record linking `user_id`, `quotation_id`, and `timestamp`
  And displays a success confirmation dialog: "Quotation QT-137836 successfully received."
```

#### AC-04.02: Attempted Receipt of Expired Quotation
```gherkin
Scenario: Normal User attempts to receive an expired quotation
  Given quotation "QT-EXPIRED-01" has expiration date "2025-01-01" (in the past)
  And status is "EXPIRED"
  When an unauthorized request or UI action attempts to call "Receive" on "QT-EXPIRED-01"
  Then the domain layer raises `QuotationExpiredException("Cannot receive an expired quotation")`
  And the action is rejected with HTTP 422 Unprocessable Entity
  And no acknowledgment record is created
```

---

### Feature 5: Expiration Management by Date & PH Renewal

#### AC-05.01: Automatic Expiration State Transition
```gherkin
Scenario: Current date surpasses quotation expiration date
  Given quotation "QT-2025-999" has status "ACTIVE" and expiration date "2026-09-24"
  When the system evaluates validity on "2026-09-25"
  Then the quotation status automatically transitions to "EXPIRED"
  And emits a `QuotationExpiredEvent`
  And the quotation is hidden from Normal User search results
```

#### AC-05.02: PH User Expired Quotation Listing
```gherkin
Scenario: PH User inspects expired quotations dashboard
  Given 3 quotations exist with status "EXPIRED"
  And 10 quotations exist with status "ACTIVE"
  When a PH User navigates to the "Expired Quotations" tab in the PH Portal
  Then the system returns a table containing exactly the 3 expired quotations
  And displays columns: Quotation ID, Vendor, Expiration Date, Days Expired, and Action Buttons
```

#### AC-05.03: PH User Refreshes / Renews Expired Quotation
```gherkin
Scenario: PH User extends expiration date of an expired quotation
  Given quotation "QT-EXPIRED-01" is currently in status "EXPIRED" with expiration date "2026-01-01"
  When a PH User opens the renewal dialog
  And inputs new expiration date "2027-12-31" and revision remarks "Vendor extended agreement"
  And clicks "[Confirm Renewal]"
  Then the system validates that "2027-12-31" is strictly greater than today
  And updates the quotation expiration date to "2027-12-31"
  And updates the status to "ACTIVE"
  And invalidates search caches
  And emits `QuotationRenewedEvent`
```

#### AC-05.04: Rejection of Invalid Renewal Date
```gherkin
Scenario: PH User submits a renewal date in the past
  Given quotation "QT-EXPIRED-01" is in status "EXPIRED"
  When a PH User attempts to set the new expiration date to "2025-12-31"
  Then the domain layer raises `InvalidValidityPeriodException("Renewal date must be in the future")`
  And the transaction is aborted
```

---

### Feature 6: Manual Quotation Request Workflow

#### AC-06.01: Normal User Submits Manual Demand
```gherkin
Scenario: Normal User submits manual quotation demand when item is not found
  Given a Normal User whose search for "Custom Mold Flange 250mm" returned no results
  When the user opens the Manual Request form
  And enters:
    | Field             | Value                            |
    | item_description  | Custom Mold Flange 250mm JIS10K  |
    | part_number       | FLG-250-JIS                      |
    | target_quantity   | 10                               |
    | target_unit       | Pcs                              |
    | needed_by_date    | 2026-11-15                       |
    | urgency           | HIGH                             |
  And clicks "[Submit Request]"
  Then the system creates a `ManualQuotationRequest` aggregate in status "SUBMITTED"
  And assigns a unique ticket ID "REQ-2026-0001"
  And displays confirmation: "Your request REQ-2026-0001 has been sent to Purchasing."
```

#### AC-06.02: Validation of Required Fields on Manual Demand
```gherkin
Scenario: Normal User submits manual demand with missing item description
  When a user attempts to submit a manual demand without an `item_description`
  Then the application rejects the submission with validation error "Item description is required"
  And no record is written to the database
```

#### AC-06.03: PH User Fulfills Manual Request with New Quotation
```gherkin
Scenario: PH User links newly uploaded quotation to an open manual request
  Given an open manual request "REQ-2026-0001" with status "SUBMITTED"
  And a new quotation "QT-2026-088" uploaded by PH
  When the PH user executes "Fulfill Request" linking "QT-2026-088" to "REQ-2026-0001"
  Then the status of "REQ-2026-0001" changes to "FULFILLED"
  And the requester receives an in-app notification with a direct link to review "QT-2026-088"
```

---

### Feature 7: PH User New Quotation Ingestion & Metadata Curation

#### AC-07.01: Successful Ingestion & Embedding Indexing
```gherkin
Scenario: PH User uploads valid PDF quotation
  Given an authenticated PH User on the Ingestion Portal
  When the user uploads "25-334.pdf"
  And the system extracts text and detects:
    | Field            | Extracted Value       |
    | quotation_number | 25-334                |
    | vendor_name      | Siam Precision Ltd.   |
    | issue_date       | 2026-01-10            |
    | expiration_date  | 2026-12-31            |
  And the PH User reviews, verifies, and clicks "[Save and Index]"
  Then a new `Quotation` aggregate is stored with status "ACTIVE"
  And the embedding engine creates a 384-dimensional dense vector
  And the vector is added to the vector store index
  And the PDF is securely saved in `storage/pdf/25-334.pdf`
```

#### AC-07.02: Ingestion Rejects Non-PDF or Corrupted Document
```gherkin
Scenario: PH User uploads non-PDF or corrupt binary
  When a user uploads a file named "spreadsheet.exe" or a 0-byte corrupt PDF
  Then the system fails fast loudly with "InvalidDocumentFormatException"
  And does NOT create a quotation or vector entry
```

---

### Feature 8: Role-Based Authorization Enforcement (RBAC)

#### AC-08.01: Normal User Blocked from Administrative Endpoints
```gherkin
Scenario: Normal User attempts to access quotation upload endpoint
  Given an authenticated user with role "NORMAL_USER"
  When the user sends a POST request to `/api/v1/quotations/ingest`
  Then the system responds with HTTP 403 Forbidden
  And logs security violation "[WARN] Unauthorized administrative access attempted by user"
```

#### AC-08.02: Normal User Blocked from Renewal Action
```gherkin
Scenario: Normal User attempts to renew an expired quotation
  Given an authenticated user with role "NORMAL_USER"
  When the user sends a POST request to `/api/v1/quotations/QT-137836/renew`
  Then the system responds with HTTP 403 Forbidden
  And no renewal operation is executed
```

---

## 3. Edge Cases, Invariants, and Resilience Matrix

| Edge Case | Expected System Behavior | Invariant / Rule |
| :--- | :--- | :--- |
| **Quotation Expires Today** | `current_date == expiration_date` is valid until 23:59:59; becomes EXPIRED at 00:00:00 next day. | `[INV-02]` |
| **Identical Quotation Number Re-uploaded** | If vendor and quotation number match an existing active quotation, system flags a conflict warning and requires explicit revision confirmation. | Rule 13 (No silent overwrite) |
| **Special Characters in Search Query** | Queries with punctuation (e.g. `M-AL6-001B__ (PMC_Minebea Thai)`) are normalized for both lexical and embedding search without regex crashes. | Robust Input Sanitization |
| **Negative Prices or Zero Quantities** | Ingestion parser rejects line items with `unit_price < 0` or `quantity <= 0`. | Domain Invariant |
| **Cache Store Unavailable** | System logs a `[WARN]` and degrades gracefully by falling back directly to the vector store, never throwing a 500 error to the end user. | High Availability |

---

## 4. Verification and Test Automation Strategy

1. **Unit Tests (`tests/unit/domain/`)**:
   - `test_quotation.py`: Tests `Quotation` lifecycle, expiration state transitions, renewal validation, and price invariants.
   - `test_validity_period.py`: Tests `ValidityPeriod` value object boundary dates.
   - `test_confidence_score.py`: Tests `ConfidenceScore` bounded interval `[0.0, 1.0]`.
   - `test_manual_quotation_request.py`: Tests `ManualQuotationRequest` submission and fulfillment invariants.
2. **Integration Tests (`tests/integration/`)**:
   - `test_vector_search.py`: Tests cosine similarity retrieval and ranking.
   - `test_search_cache.py`: Tests query hashing, cache hit/miss, and eviction.
   - `test_pdf_ingestion.py`: Tests PDF text parsing and metadata extraction.
3. **API / Interface Tests (`tests/interfaces/`)**:
   - `test_search_api.py`: Tests HTTP search endpoints and JSON responses.
   - `test_rbac_security.py`: Tests role permission enforcement (HTTP 403).
