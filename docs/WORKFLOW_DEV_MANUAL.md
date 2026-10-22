# Suppier: Developer Workflow Manual (คู่มือการทำงานและผังการทำงานทั้งหมดของระบบ)

> **Enterprise Procurement & Requisition Platform for MinebeaMitsumi (Thailand) Co., Ltd.**  
> Target Facilities: Bang Pa-in (BPI) & Rojana Plant Operations  
> Document Version: 2.0.0 (Comprehensive System Workflows)  
> Applicable Services: Frontend (Angular 18), Backend (Express.js :5000), AI Quotation Microservice (Python FastAPI :8000)

---

## 📑 Table of Contents

1. [System Macro-Architecture & Orchestration Workflow](#1-system-macro-architecture--orchestration-workflow)
   - 1.1 Tri-Service Runtime Topology
   - 1.2 System Bootstrapping & Launcher Lifecycle (`start.bat` / `stop.bat`)
   - 1.3 Communication Protocol & API Gateway Matrix
   - 1.4 Role-Based Operational Persona Matrix
2. [End-to-End Core System Workflows (Detailed Mermaid Sequences)](#2-end-to-end-core-system-workflows)
   - [WF-01: Employee OTP Authentication & Session Bootstrapping](#wf-01-employee-otp-authentication--session-bootstrapping)
   - [WF-02: Requisition Header & Item Grid Lifecycle (CRUD & Atomic Persistence)](#wf-02-requisition-header--item-grid-lifecycle-crud--atomic-persistence)
   - [WF-03: Technical Drawing & Document Attachment Ingestion](#wf-03-technical-drawing--document-attachment-ingestion)
   - [WF-04: Purchasing Aggregation & MinebeaMitsumi Branded Email Builder](#wf-04-purchasing-aggregation--minebeamitsumi-branded-email-builder)
   - [WF-05: Google SERP & Shopee Hybrid Quotation Search Engine](#wf-05-google-serp--shopee-hybrid-quotation-search-engine)
   - [WF-06: Hybrid Vector & Lexical Search Pipeline (Port 8000)](#wf-06-hybrid-vector--lexical-search-pipeline-port-8000)
   - [WF-07: Conversational AI Procurement Copilot (RAG Pipeline)](#wf-07-conversational-ai-procurement-copilot-rag-pipeline)
   - [WF-08: Zero-Input Smart PDF Auto-Extraction & Batch Ingestion](#wf-08-zero-input-smart-pdf-auto-extraction--batch-ingestion)
   - [WF-09: Human-in-the-Loop (HITL) Staging, Validation & Curation](#wf-09-human-in-the-loop-hitl-staging-validation--curation)
   - [WF-10: Conversational Slot-Filling Agent for Automated RFQ / PR Generation](#wf-10-conversational-slot-filling-agent-for-automated-rfq--pr-generation)
   - [WF-11: Historical Price Trend Analytics & Anomaly Detection](#wf-11-historical-price-trend-analytics--anomaly-detection)
   - [WF-12: Quotation Expiration Lifecycle & Proactive Alert Scanner](#wf-12-quotation-expiration-lifecycle--proactive-alert-scanner)
   - [WF-13: 3D Flipping Employee ID Badge & 2026 Shift Calendar Navigation](#wf-13-3d-flipping-employee-id-badge--2026-shift-calendar-navigation)
   - [WF-14: Failover, Graceful Degradation & In-Memory Offline Modes](#wf-14-failover-graceful-degradation--in-memory-offline-modes)
3. [Data State Machines & Database Lifecycle Models](#3-data-state-machines--database-lifecycle-models)
   - 3.1 Requisition Document State Machine
   - 3.2 Quotation Aggregate Lifecycle
   - 3.3 Manual Quotation Demand Lifecycle
   - 3.4 HITL Staging Verification Lifecycle
   - 3.5 Database Schemas & Storage Topologies (MSSQL vs SQLite)
4. [Developer Implementation, Extension & Debugging Guide](#4-developer-implementation-extension--debugging-guide)
   - 4.1 How to Implement a New Feature End-to-End
   - 4.2 Automated Testing & Validation Workflows
   - 4.3 Structured Telemetry, Logging & Coding Standards
   - 4.4 Troubleshooting Runbook & Known Gotchas

---

## 1. System Macro-Architecture & Orchestration Workflow

### 1.1 Tri-Service Runtime Topology

Suppier operates as a decoupled, multi-tier hybrid system consisting of three autonomous runtimes working in unison:

```mermaid
graph TB
    subgraph Browser_Tier [Client Presentation Layer - Port 4200]
        SPA["Angular 18 Standalone SPA (app.component.ts)"]
        UI_REQ["Requisition Grid & Summary Panel"]
        UI_SRCH["Google / Shopee Hybrid Search Engine"]
        UI_PURCH["Purchase View & Outlook Email Builder"]
        UI_CARD["3D Employee Badge & 2026 Shift Calendar"]
        UI_COPILOT["AI Procurement Copilot Widget"]
        GW["api.service.ts (Unified Client Gateway)"]
    end

    subgraph Backend_Tier [Core Requisition & Auth Gateway - Node.js Express :5000]
        EXP["server.js (Express Application & 50MB Body Parser)"]
        AUTH_ROUTER["routes/auth.routes.js"]
        REQ_ROUTER["routes/requisition.routes.js"]
        AUTH_CTRL["controllers/auth.controller.js"]
        REQ_CTRL["controllers/requisition.controller.js"]
        DB_POOL["config/db.js (MSSQL Connection Pool)"]
        FS_ATTACH["backend/uploads/attachments/ (Local Disk)"]
    end

    subgraph AI_Microservice_Tier [Quotation Discovery & AI Engine - Python FastAPI :8000]
        API_APP["main.py -> src/interfaces/web_app.py"]
        APP_SVC["QuotationApplicationService (Orchestrator)"]
        INQ_SVC["QuotationInquiryService (RAG Copilot)"]
        SLOT_AGENT["SlotFillingAgent (Automated RFQ / PR)"]
        HITL_SVC["HitlVerificationService (Human-in-the-Loop)"]
        PRICE_SVC["PriceAnalyticsService (Price Trends & Alerts)"]
        PDF_PARSER["PdfDocumentReader (Smart Heuristic Parser)"]
        VISION_LLM["VisionLlmQuotationExtractor (Multi-modal)"]
        HYBRID_RERANK["HybridReranker (RRF + Cross-Encoder)"]
        BM25["BM25Index (Lexical Inverted Index)"]
        VEC_IDX["MemoryVectorIndex (FastEmbed 384-dim ONNX)"]
        CACHE_SEARCH["SearchCache (SHA-256 In-Memory)"]
        CACHE_INQ["InquiryCache (SHA-256 In-Memory)"]
        SQLITE_REPO["SqliteQuotationRepository (quotations.db)"]
        GEMINI_GEN["GeminiAnswerGenerator (gemini-2.5-flash)"]
    end

    subgraph Data_Storage_Tier [Enterprise Persistence & Fallback Stores]
        MSSQL[("Microsoft SQL Server PBGM8G\n[Suppier] DB")]
        CSV[("Master_Employee.csv (Offline Fallback)")]
        SQLITE_DB[("quotations.db (SQLite WAL Mode)")]
        PDF_VAULT[("storage/pdf/ (Vendor PDF Originals)")]
        STAGING_VAULT[("storage/staging/ (HITL Uncommitted Drafts)")]
    end

    %% Client Gateway Connections
    SPA --> GW
    GW -->|HTTP /api/auth/*| AUTH_ROUTER
    GW -->|HTTP /api/requisition/*| REQ_ROUTER
    GW -->|HTTP GET /api/search| API_APP
    GW -->|HTTP POST /api/inquiry/ask-json| API_APP
    GW -->|HTTP POST /api/quotations/extract-preview| API_APP
    GW -->|HTTP POST /api/quotations/batch-commit| API_APP

    %% Backend Routing & Persistence
    AUTH_ROUTER --> AUTH_CTRL
    REQ_ROUTER --> REQ_CTRL
    AUTH_CTRL --> DB_POOL
    REQ_CTRL --> DB_POOL
    REQ_CTRL -->|Disk Write| FS_ATTACH
    DB_POOL -->|TDS Port 1433| MSSQL
    AUTH_CTRL -.->|Fallback on Disconnect| CSV

    %% Microservice Routing & Persistence
    API_APP --> APP_SVC
    API_APP --> INQ_SVC
    API_APP --> SLOT_AGENT
    API_APP --> HITL_SVC
    API_APP --> PRICE_SVC
    APP_SVC --> HYBRID_RERANK
    HYBRID_RERANK --> BM25
    HYBRID_RERANK --> VEC_IDX
    APP_SVC --> CACHE_SEARCH
    INQ_SVC --> CACHE_INQ
    INQ_SVC --> GEMINI_GEN
    APP_SVC --> SQLITE_REPO
    SQLITE_REPO --> SQLITE_DB
    APP_SVC --> PDF_PARSER
    PDF_PARSER --> PDF_VAULT
    HITL_SVC --> VISION_LLM
    HITL_SVC --> STAGING_VAULT
```

---

### 1.2 System Bootstrapping & Launcher Lifecycle (`start.bat` / `stop.bat`)

The entire ecosystem is orchestrated via Windows batch automation:

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / Operator
    participant BAT as start.bat
    participant BE as Backend (:5000)
    participant PY as AI Microservice (:8000)
    participant NG as Frontend (:4200)
    participant EDGE as Microsoft Edge Browser

    Dev->>BAT: Double-click start.bat
    BAT->>BAT: Set UTF-8 code page (chcp 65001)
    
    BAT->>BE: start cmd /k npm start (Cwd: /backend)
    Note over BE: Launches Node.js Express server<br/>Connects to MSSQL Pool PBGM8G<br/>Listens on http://localhost:5000
    
    BAT->>PY: start cmd /k .venv\Scripts\python.exe main.py (Cwd: /ai_quotation)
    Note over PY: Configures .cache paths on Drive D:<br/>Loads FastEmbed BGE model into ONNX<br/>Initializes SQLite DB & auto-seeds<br/>Listens on http://localhost:8000
    
    BAT->>NG: start cmd /k npm start (Cwd: /)
    Note over NG: Launches Angular Dev Server (ng serve)<br/>Compiles standalone components & Tailwind<br/>Listens on http://localhost:4200
    
    BAT->>BAT: ping 127.0.0.1 -n 7 (Waits 6 seconds for port binding)
    BAT->>EDGE: start msedge.exe http://localhost:4200
    EDGE->>NG: GET http://localhost:4200 (Loads Application Shell)
```

**Shutdown Sequence (`stop.bat`)**:
1. Locates process IDs bound to TCP ports `5000`, `8000`, and `4200` via `netstat -ano`.
2. Issues `taskkill /F /PID <pid>` for each service process.
3. Cleans temporary lock files to ensure graceful subsequent startups.

---

### 1.3 Communication Protocol & API Gateway Matrix

| Client Component | Target Service | Path / Endpoint | Protocol / Method | Payload Type | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | Backend (:5000) | `/api/auth/verify-employee` | HTTP POST | JSON (`{ employeeId }`) | Validates 5-digit employee code against `Master_Employee`. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | Backend (:5000) | `/api/requisition/account/:empNo` | HTTP GET | URL Param | Fetches current draft requisition and line items for logged-in user. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | Backend (:5000) | `/api/requisition/save-all` | HTTP POST | JSON (`{ header, items, empNo }`) | Atomic transactional upsert of header and all line items. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | Backend (:5000) | `/api/requisition/upload` | HTTP POST | JSON (`{ fileName, fileData }`) | Ingests Base64 file attachments up to 50MB to disk. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | Backend (:5000) | `/api/requisition/all` | HTTP GET | None | Fetches all pending quotations across plant for buyer review. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/search` | HTTP GET | Query Params (`query`, `user_role`) | Hybrid dense/sparse quotation search with role price masks. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/inquiry/ask-json` | HTTP POST | FormData (`query`, `user_role`) | RAG conversational inquiry answering via Gemini 2.5 Flash. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/quotations/extract-preview`| HTTP POST | Multipart/Form-Data (`file`) | Smart PDF extraction preview (Zero-input metadata extraction). |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/quotations/batch-commit` | HTTP POST | JSON (`{ drafts }`) | Commits verified PDF quotation drafts into SQLite repository. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/chat/slot-filling` | HTTP POST | JSON (`{ session_id, message }`)| Multi-turn dialogue agent collecting RFQ/PR specifications. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/hitl/stage` | HTTP POST | Multipart/Form-Data (`file`) | Ingests PDF into uncommitted HITL staging vault. |
| [api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) | AI Service (:8000) | `/api/analytics/price-trend` | HTTP GET | Query Param (`part_query`) | Historical price trend analysis and anomaly detection. |

---

### 1.4 Role-Based Operational Persona Matrix

```mermaid
journey
    title Suppier Multi-Persona Workflow Journey
    section Factory Operator
      Enter 5-Digit OTP (e.g. X4770): 5: Operator
      Input Damaged Part Details & Spec: 4: Operator
      Upload Technical Drawing PDF: 5: Operator
      Save Requisition Document: 5: Operator
    section Section Supervisor
      Review Incoming Requisitions: 4: Supervisor
      Prioritize (Normal vs Urgent): 5: Supervisor
      Assign Budget Division & Approve: 5: Supervisor
    section Purchasing Buyer (P/H)
      Aggregate Multi-Section Requests: 5: Buyer
      Search Live Catalog & PDF Quotes: 5: Buyer
      Generate Outlook Cyan Email: 5: Buyer
      Batch Ingest Vendor Quotation PDFs: 5: Buyer
    section AI Copilot & Engine
      Semantic Vector & BM25 Search: 5: AI Engine
      Conversational RAG Answers: 5: AI Engine
      Interactive Slot-Filling for PRs: 5: AI Engine
      Proactive Expiration Scanning: 4: AI Engine
```

---

## 2. End-to-End Core System Workflows

### WF-01: Employee OTP Authentication & Session Bootstrapping

This workflow validates factory employees using their 5-digit badge number, animates the orbital convergence visual effect, loads their personalized identity, and restores the active requisition draft.

```mermaid
sequenceDiagram
    autonumber
    actor Emp as Factory Operator / Engineer
    participant UI as Login Screen (app.component.html)
    participant AC as AppComponent (app.component.ts)
    participant AS as ApiService (api.service.ts)
    participant BE as auth.controller.js (Port 5000)
    participant DB as MSSQL [Suppier].[dbo].[Master_Employee]
    participant CSV as Master_Employee.csv (Fallback)
    participant STORE as Browser localStorage

    Emp->>UI: Types 5-digit Employee ID (e.g., "X4770")
    UI->>AC: onCodeChange("X4770")
    AC->>AC: Regex check: /^[A-Z0-9]{5}$/
    AC->>UI: Sets loginPhase = 'rotating' (5 orbital nodes rotate at 72° offsets)
    AC->>UI: Sets loginPhase = 'converging' (Nodes smoothly collapse to center point)
    
    AC->>AS: verifyEmployee("X4770")
    AS->>BE: POST /api/auth/verify-employee { employeeId: "X4770" }
    
    alt MSSQL Database Online
        BE->>DB: SELECT e.*, d.Div_Name, s.Sec_Name FROM Master_Employee e ... WHERE Emp_No = 'X4770'
        DB-->>BE: Returns employee record (MR. DANUPHON SUTTHIWATTHANAK)
    else MSSQL Disconnected (Graceful Fallback)
        BE->>CSV: Stream & parse Master_Employee.csv for Emp_No == 'X4770'
        CSV-->>BE: Returns cached employee record
    end

    BE->>BE: cleanEmployeeName() -> "DANUPHON SUTTHIWATTHANAK"
    BE->>BE: Map Thai name "ดนุพล สุทธิวัฒนกุล", Division "MA", Section "M/M"
    BE-->>AS: 200 OK { success: true, user: EmployeeUser }
    AS-->>AC: Returns EmployeeUser payload

    AC->>UI: Sets loginPhase = 'downloading' (Progress counter 0% -> 100%)
    AC->>STORE: localStorage.setItem('suppier_emp_no', 'X4770')
    AC->>STORE: localStorage.setItem('suppier_user_profile', JSON.stringify(user))
    AC->>AC: currentUser = user, isLoggedIn = true
    
    AC->>AS: getDocumentByAccount("X4770")
    AS->>BE: GET /api/requisition/account/X4770
    BE-->>AS: 200 OK { header, items }
    AS-->>AC: Binds existing draft or personal empty template
    
    AC->>UI: Unmounts Login Screen; Mounts Master Header & Left Navigation
```

---

### WF-02: Requisition Header & Item Grid Lifecycle (CRUD & Atomic Persistence)

Manages line item insertion, real-time formula evaluation (Quantity × Price = Total), dynamic division budget checks, and atomic database persistence with transactional rollback safety.

```mermaid
sequenceDiagram
    autonumber
    actor Tech as Maintenance Engineer
    participant UI as Data Table Grid
    participant AC as AppComponent
    participant AS as ApiService
    participant BE as requisition.controller.js
    participant TX as SQL Server Transaction Manager
    participant DB as MSSQL Tables (Requisitions & RequisitionItems)

    Tech->>UI: Clicks "+ เพิ่มรายการ" (Add Line Item)
    UI->>AC: addRow()
    AC->>AC: Calculates next ItemNo, creates RequisitionItem with default status
    AC->>UI: Renders new row with item.isEditing = true
    
    Tech->>UI: Inputs PartName="AIR CYLINDER", Maker="SMC", Qty=2, UnitPrice=1450.00
    UI->>AC: calculateTotals()
    AC->>AC: item.amount = item.quantity * item.unitPrice (2900.00)
    AC->>AC: header.totalCost = sum(all active item amounts)
    AC->>UI: Re-renders sticky summary footer in real-time
    
    Tech->>UI: Clicks "บันทึกข้อมูลทั้งหมด" (Save Entire Document)
    UI->>AC: saveEntireDocument()
    AC->>AC: Validates header required fields (Division, Section, Date)
    AC->>AS: saveEntireDocument(docNumber, header, requisitionItems, empNo)
    AS->>BE: POST /api/requisition/save-all { header, items, empNo }

    BE->>TX: const transaction = new sql.Transaction(pool); await transaction.begin()
    
    rect rgb(240, 248, 255)
        Note over BE, DB: Atomic Transaction Boundary
        BE->>DB: MERGE INTO Requisitions (Header Record)
        BE->>DB: DELETE FROM RequisitionItems WHERE DocNumber = @docNumber
        loop For each item in items array
            BE->>DB: INSERT INTO RequisitionItems (DocNumber, ItemNo, PartName, Spec, Maker, Qty, Price, AttachmentsJson)
        end
    end

    alt Success on All Inserts
        BE->>TX: await transaction.commit()
        BE-->>AS: 200 OK { success: true, message: "บันทึกสำเร็จ" }
        AS-->>AC: Returns true
        AC->>AC: Sets isEditingAllRows = false, clears dirty snapshots
        AC->>UI: Displays green toast: "บันทึกข้อมูล Requisition และรายการทั้งหมดสำเร็จ"
    else Error Detected on Any Item
        BE->>TX: await transaction.rollback()
        BE-->>AS: 500 Error { success: false, message: "Database rollback triggered" }
        AS-->>AC: Returns false
        AC->>UI: Displays red error banner: "เกิดข้อผิดพลาดในการบันทึกข้อมูล กรุณาลองใหม่อีกครั้ง"
    end
```

---

### WF-03: Technical Drawing & Document Attachment Ingestion

Enables operators to attach CAD drawings, spec sheets, and vendor quote PDFs directly to any requisition line item.

```mermaid
sequenceDiagram
    autonumber
    actor Tech as Technician
    participant UI as Item Row File Input
    participant AC as AppComponent
    participant AS as ApiService
    participant BE as requisition.controller.js
    participant FS as Local Storage (/backend/uploads/attachments)

    Tech->>UI: Clicks "Attach Drawing" & selects "Cylinder_Mounting.pdf" (12MB)
    UI->>AC: onAttachmentFileSelected(event, itemIndex)
    AC->>AC: Validates file extension (.pdf, .jpg, .png, .dwg) and file size (<50MB)
    AC->>AC: Uses FileReader.readAsDataURL() -> Generates Base64 string
    
    AC->>AS: uploadAttachment({ fileName: "Cylinder_Mounting.pdf", fileData: "data:application/pdf;base64,..." })
    AS->>BE: POST /api/requisition/upload (Express body limit: 50MB)
    
    BE->>BE: Strips Base64 data URI scheme header
    BE->>BE: Generates unique collision-free filename: Date.now() + "_" + sanitizedName
    BE->>FS: fs.promises.writeFile(filePath, buffer)
    
    BE-->>AS: 200 OK { success: true, file: { fileName, originalName, url: "http://localhost:5000/uploads/attachments/..." } }
    AS-->>AC: Appends uploaded file metadata to item.attachments array
    AC->>AC: Marks item as dirty (unsaved changes)
    AC->>UI: Renders clickable attachment badge with preview/download link
```

---

### WF-04: Purchasing Aggregation & MinebeaMitsumi Branded Email Builder

Purchasing officers (P/H section) aggregate quotation requests from multiple departments, filter them, and generate an Outlook-ready HTML table styled in authentic MinebeaMitsumi corporate cyan.

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Purchasing Officer (P/H)
    participant UI as Purchase View UI
    participant AC as AppComponent
    participant AS as ApiService
    participant CLIP as Browser Clipboard API (ClipboardItem)
    participant OUT as Microsoft Outlook

    Buyer->>UI: Navigates to "Purchase View" Tab
    UI->>AC: openPurchaseQuotationView() -> loadAllQuotationRequests()
    AC->>AS: getAllQuotationRequests()
    AS-->>AC: Returns array of pending Requisitions across all plant sections
    AC->>UI: Renders multi-request aggregation master list
    
    Buyer->>UI: Selects checkboxes for DOC-2026-0901-003 and DOC-TRISAK-01
    UI->>AC: toggleRequestSelection(docNumber)
    AC->>AC: updateSelectedItemsAndSubject()
    AC->>AC: Formats subject: "Request Quotation to Purchase (MA - M/M - PMA) [DOC-2026-0901-003, DOC-TRISAK-01] 2026-10-21"
    AC->>UI: Live preview renders MinebeaMitsumi Cyan Table (#00bcd4 header, alternate row shading)
    
    Buyer->>UI: Clicks "Copy Email (HTML)"
    UI->>AC: copyEmailQuotationToClipboard()
    AC->>AC: buildEmailHtml(selectedItems) -> Constructs complete HTML DOM with CSS inline styles
    
    alt Modern Browser ClipboardItem Supported
        AC->>CLIP: navigator.clipboard.write([ new ClipboardItem({ 'text/html': htmlBlob, 'text/plain': textBlob }) ])
    else Insecure Origin / Legacy Fallback
        AC->>AC: fallbackCopyHtml(html) -> Hidden contenteditable DIV + document.execCommand('copy')
    end

    AC->>UI: Floating success toast: "คัดลอกตารางใบขอเสนอราคา (HTML) ลง Clipboard เรียบร้อยแล้ว"
    Buyer->>OUT: Opens Outlook New Email -> Presses Ctrl+V
    OUT->>OUT: Pastes perfectly formatted Cyan Table with intact borders, alignments, and signature
```

---

### WF-05: Google SERP & Shopee Hybrid Quotation Search Engine

The unified search experience combines Google's fast SERP layout with Shopee's visual e-commerce product grid, complete with 1-click requisition cart import.

```mermaid
sequenceDiagram
    autonumber
    actor User as Buyer / Maintenance Tech
    participant UI as Search Engine View
    participant AC as AppComponent
    participant AS as ApiService
    participant MS as AI Microservice (:8000)

    User->>UI: Types "SMC CYLINDER MGPM" in Google search bar, presses Enter
    UI->>AC: executeQuotationSearch("SMC CYLINDER MGPM")
    AC->>AC: Appends query to recentSearches in localStorage
    AC->>AC: Executes local fuzzy scoring across cached catalog
    
    AC->>AS: searchSupplierQuotations("SMC CYLINDER MGPM", "NORMAL_USER")
    AS->>MS: GET /api/search?query=SMC+CYLINDER+MGPM&user_role=NORMAL_USER
    MS-->>AS: 200 OK { count: 4, results: [ { quotation_number, vendor_name, items: [...] } ] }
    AS-->>AC: Binds results to supplierQuotationsResult
    
    AC->>UI: Displays SERP results with Knowledge Graph sidebar (Maker info, price curve)
    
    User->>UI: Clicks "Shopee Grid View" toggle button
    UI->>AC: setResultViewLayout('shopee')
    AC->>UI: Transforms list into Shopee product cards (discount tags, star ratings, CAD badges)
    
    User->>UI: Clicks "Add to Requisition" on target line item
    UI->>AC: addToRequisitionCart(item)
    AC->>AC: Instantiates new RequisitionItem pre-populated with:
    Note over AC: PartName: item.item_name<br/>Spec: item.specification<br/>UnitPrice: item.unit_price<br/>Vendor: item.vendor_name<br/>QuotationNo: item.quotation_number
    AC->>AC: Appends to requisitionItems array
    AC->>UI: Displays toast: "เพิ่มรายการ [SMC CYLINDER MGPM] ลงในใบขอซื้อสำเร็จ"
```

---

### WF-06: Hybrid Vector & Lexical Search Pipeline (Port 8000)

The search engine inside `ai_quotation` executes a two-stage hybrid retrieval strategy: fast in-memory caching, parallel dense semantic vector retrieval via FastEmbed ONNX, sparse keyword matching via BM25, Reciprocal Rank Fusion (RRF), and Cross-Encoder reranking.

```mermaid
flowchart TD
    START([User Submits Search Query]) --> NORM[Query Normalization & Tokenization]
    NORM --> CACHE_CHK{SHA-256 Hash in SearchCache?}
    
    CACHE_CHK -- Cache Hit (<0.05ms) --> RET_CACHE[Return Cached Ranked Results]
    RET_CACHE --> ROLE_MASK
    
    CACHE_CHK -- Cache Miss (~25ms) --> DUAL_RETRIEVAL[/Initiate Parallel Dual Retrieval/]
    
    subgraph Parallel_Retrieval [Two-Stage Dual Retrieval]
        DUAL_RETRIEVAL --> DENSE_PATH[FastEmbed ONNX Engine\nDense 384-dim Embedding\nBAAI/bge-small-en-v1.5]
        DUAL_RETRIEVAL --> SPARSE_PATH[BM25 Lexical Index\nMultilingual Token Matcher\nThai, Japanese, Model Codes]
        
        DENSE_PATH --> COSINE[Cosine Similarity Calculation\nOver Indexed Quotation Chunks]
        SPARSE_PATH --> BM25_SCORE[BM25Okapi Scoring & Field Boosting]
    end
    
    COSINE --> RRF[Reciprocal Rank Fusion\nk = 60, weight_vector = 0.5, weight_bm25 = 0.5]
    BM25_SCORE --> RRF
    
    RRF --> TOP_CANDIDATES[Top-25 Fused Candidates]
    TOP_CANDIDATES --> RERANK[Cross-Encoder Reranker\nms-marco-MiniLM-L-6-v2]
    RERANK --> CACHE_PUT[Store Results in SearchCache with TTL]
    CACHE_PUT --> ROLE_MASK{User Role Check}
    
    ROLE_MASK -- NORMAL_USER --> MASK_PRICE[Mask Supplier Margins & Commercial Terms]
    ROLE_MASK -- PH_USER --> RAW_PRICE[Expose Raw Unit Prices & Historical Margins]
    
    MASK_PRICE --> RESP([Return JSON Response to Client])
    RAW_PRICE --> RESP
```

---

### WF-07: Conversational AI Procurement Copilot (RAG Pipeline)

The AI Copilot operates a Retrieval-Augmented Generation (RAG) architecture grounded strictly in verified vendor quotation documents.

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as P/H Buyer or Engineer
    participant UI as Copilot Chat Drawer
    participant AC as AppComponent
    participant AS as ApiService
    participant MS as AI Microservice (:8000)
    participant CACHE as In-Memory InquiryCache
    participant SQLITE as quotations.db
    participant GEMINI as Google Gemini 2.5 Flash API

    Buyer->>UI: Types question: "สายพาน Bando B-42 มีเจ้าไหนเสนอราคาต่ำสุด และส่งของกี่วัน?"
    UI->>AC: askAiQuotation(query)
    AC->>AS: askAiQuotationInquiry(query, "PH_USER")
    AS->>MS: POST /api/inquiry/ask-json (FormData)
    
    MS->>MS: Normalize query string, compute SHA-256 key
    MS->>CACHE: Check InquiryCache(key)
    
    alt Cache Hit (<1ms)
        CACHE-->>MS: Cached answer, citations, and telemetry
    else Cache Miss (~1400ms)
        MS->>SQLITE: Query active quotations matching tokens "Bando", "B-42", "สายพาน"
        SQLITE-->>MS: Returns 3 matching line items from 2 vendors (MISUMI, PNEUMAX)
        MS->>MS: Assemble RAG Context: Vendor, Unit Price, Lead Time, Valid Dates, Raw Snippet
        
        MS->>GEMINI: Generate grounded completion with strict system prompt
        Note over GEMINI: Invariants Enforced:<br/>1. Ground answers strictly on provided context<br/>2. If price is missing, state unknown<br/>3. Format citations as [QuotationNo]
        GEMINI-->>MS: Grounded synthesis text
        
        MS->>MS: Parse citations into QuotationCitationView DTOs
        MS->>CACHE: Put answer & citations into InquiryCache (TTL: 3600s)
    end

    MS-->>AS: 200 OK { answer, citations: [...], duration_ms: 1380, cache_hit: false }
    AS-->>AC: Binds aiInquiryResult
    AC->>UI: Renders Markdown response with interactive badges:
    Note over UI: - [Research] button (triggers SERP search)<br/>- [PDF] button (opens original vendor document modal)
```

---

### WF-08: Zero-Input Smart PDF Auto-Extraction & Batch Ingestion

Allows purchasing officers to drag and drop multiple vendor quotation PDFs without manual typing. The engine automatically detects the vendor header, converts Buddhist Era to Gregorian years, parses item tables, and registers them in the database.

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Purchasing Officer (P/H)
    participant PORTAL as PH Workbench Portal
    participant MS as AI Microservice (:8000)
    participant RDR as PdfDocumentReader (pdf_reader.py)
    participant SQLITE as SqliteQuotationRepository
    participant VEC as Vector & BM25 Indexes

    Officer->>PORTAL: Drags and drops 10 PDF quotation files
    PORTAL->>MS: POST /api/quotations/batch-preview (multipart/form-data)
    
    loop For each uploaded PDF file
        MS->>RDR: extract_draft(pdf_bytes, filename)
        RDR->>RDR: PyPDF extracts text stream & SHA-256 fingerprint
        RDR->>RDR: Detect vendor via header regex & tax ID heuristics (e.g. SMC, MISUMI)
        RDR->>RDR: Convert Buddhist Era dates: if year > 2400 then year = year - 543
        RDR->>RDR: Tabular bounding box parser extracts lines: ItemNo, PartName, Spec, Qty, Price
        RDR-->>MS: Returns ExtractedQuotationDraft DTO
    end

    MS-->>PORTAL: 200 OK with extracted preview table for all 10 documents
    Officer->>PORTAL: Reviews extracted drafts, adjusts any ambiguous field, clicks "Confirm All Ingestions"
    PORTAL->>MS: POST /api/quotations/batch-commit { drafts: [...] }
    
    MS->>SQLITE: Batch INSERT into quotations and quotation_items
    MS->>VEC: Trigger incremental FastEmbed dense embedding & BM25 index refresh
    MS-->>PORTAL: 200 OK { success: true, count: 10 }
    PORTAL->>Officer: Displays green success banner; updates active KPI dashboard
```

---

### WF-09: Human-in-the-Loop (HITL) Staging, Validation & Curation

When a vendor quotation PDF has irregular formatting, handwriting, or low extraction confidence, it is routed into the Human-in-the-Loop staging vault where procurement specialists can review, edit, and audit before final database commitment.

```mermaid
stateDiagram-v2
    [*] --> Upload_PDF: Officer uploads unverified vendor PDF
    Upload_PDF --> Vision_LLM_Staging: POST /api/hitl/stage
    
    state Vision_LLM_Staging {
        [*] --> Save_Staging_File: Save to storage/staging/STAGE-{UUID}
        Save_Staging_File --> Extract_Vision_LLM: Multimodal extraction
        Extract_Vision_LLM --> Validate_Invariants: Check expiration >= issue_date, positive price
    }
    
    Vision_LLM_Staging --> PENDING_VERIFICATION: Create StagedQuotationDraft
    
    state PENDING_VERIFICATION {
        Review_Draft --> Edit_Fields: User corrects Vendor, Line Items, Unit Prices
        Edit_Fields --> Review_Diff: Highlight modified fields in Amber
    }
    
    PENDING_VERIFICATION --> VERIFIED_COMMITTED: POST /api/hitl/drafts/{id}/commit
    PENDING_VERIFICATION --> DISCARDED: POST /api/hitl/drafts/{id}/discard
    
    state VERIFIED_COMMITTED {
        Move_File: Move PDF from storage/staging to storage/pdf
        Insert_DB: Commit to quotations.db
        Reindex: Update FastEmbed ONNX & BM25 Indexes
    }
    
    state DISCARDED {
        Purge_File: Delete temporary staged file from disk
    }
    
    VERIFIED_COMMITTED --> [*]
    DISCARDED --> [*]
```

---

### WF-10: Conversational Slot-Filling Agent for Automated RFQ / PR Generation

When an engineer searches for a spare part that does not exist in the database, the conversational Slot-Filling Agent automatically intervenes to collect missing requirements and draft a Purchase Requisition (PR) / Request for Quotation (RFQ).

```mermaid
sequenceDiagram
    autonumber
    actor Tech as Factory Engineer
    participant UI as Requisition / Chat Interface
    participant AC as AppComponent
    participant AS as ApiService
    participant AGENT as SlotFillingAgent (slot_filling_agent.py)
    participant REPO as SqliteManualRequestRepository

    Tech->>UI: Searches for "Hydraulic Solenoid Valve D03" -> 0 matches found
    UI->>AC: Empty search detected
    AC->>AS: triggerFromEmptySearch("Hydraulic Solenoid Valve D03")
    AS->>AGENT: trigger_from_empty_search(session_id, "Hydraulic Solenoid Valve D03")
    
    AGENT->>AGENT: Initialize ConversationSession (step: "COLLECTING")
    AGENT->>AGENT: SlotState.item_name = "Hydraulic Solenoid Valve D03"
    AGENT-->>AS: Returns prompt: "ระบบพร้อมจัดทำแบบร่าง RFQ อัตโนมัติ กรุณาระบุสเปก, จำนวน, และความเร่งด่วน"
    AS-->>UI: Displays assistant message bubble in chat drawer
    
    Tech->>UI: Replies: "สเปก 24VDC 5000psi ต้องการ 3 ตัว ด่วนมาก"
    UI->>AC: sendMessage(text)
    AC->>AS: processUserMessage(session_id, text)
    AS->>AGENT: process_user_message(session_id, text)
    
    AGENT->>AGENT: Regex & Heuristic Slot Extraction:
    Note over AGENT: specification: "24VDC 5000psi"<br/>quantity: 3.0<br/>unit: "Pcs"<br/>urgency: "CRITICAL"
    
    alt All Required Slots Filled
        AGENT->>AGENT: Transition step to "CONFIRMING"
        AGENT->>AGENT: Generate PrRfqDraft with unique rfq_number (e.g. RFQ-2026-A4B1)
        AGENT-->>AS: Returns draft summary and confirmation request
        AS-->>UI: Renders formatted PR/RFQ Draft card with "ยืนยันการจัดทำ PR" button
        
        Tech->>UI: Clicks "ยืนยันการจัดทำ PR"
        UI->>AGENT: confirmDraft(session_id)
        AGENT->>REPO: Persist ManualQuotationRequest aggregate into database
        AGENT->>AGENT: Step = "COMPLETED"
        AGENT-->>UI: "สร้างเอกสารขอซื้อเรียบร้อยแล้ว ส่งไปยังแผนกจัดซื้อเรียบร้อยครับ"
    else Missing Critical Slots
        AGENT-->>AS: Asks targeted follow-up question for remaining empty slots
        AS-->>UI: Displays follow-up prompt to user
    end
```

---

### WF-11: Historical Price Trend Analytics & Anomaly Detection

Procurement analysts query historical quotation records to detect price spikes, downward trends, and vendor pricing variations before issuing purchase orders.

```mermaid
flowchart TD
    QUERY([User Requests Price Trend for Component]) --> FETCH[Query Sqlite Database for all line items matching Part/Spec]
    FETCH --> SORT[Sort Historical Price Points by Date Ascending]
    
    subgraph Analytics_Calculation [PriceAnalyticsService]
        SORT --> STATS[Compute Statistical Metrics:\n- Minimum Price\n- Maximum Price\n- Average Price\n- Latest Price]
        STATS --> DIFF[Calculate Price Change Percentage:\n((Latest - Avg) / Avg) * 100]
        
        DIFF --> DIRECTION{Evaluate Trend Direction}
        DIRECTION -- Change > +5% --> DIR_UP[Trend: UP\nFlag Potential Cost Increase]
        DIRECTION -- Change < -5% --> DIR_DOWN[Trend: DOWN\nFlag Favorable Negotiation Window]
        DIRECTION -- Between -5% and +5% --> DIR_STABLE[Trend: STABLE\nStable Historical Pricing]
    end
    
    DIR_UP --> ANOMALY{Is Latest Price > 1.25 * Max Previous?}
    DIR_DOWN --> REC
    DIR_STABLE --> REC
    
    ANOMALY -- Yes --> ALERT[Generate SystemAlert: PRICE_INCREASE\nSeverity: WARNING]
    ANOMALY -- No --> REC[Synthesize Procurement Recommendation]
    
    ALERT --> OUT([Return PriceTrendAnalysis & Recommendation DTO])
    REC --> OUT
```

---

### WF-12: Quotation Expiration Lifecycle & Proactive Alert Scanner

Ensures the factory never issues requisitions against expired or superseded vendor quotation agreements.

```mermaid
sequenceDiagram
    autonumber
    actor Cron as Automated Scanner / P/H Buyer
    participant MS as AI Microservice (:8000)
    participant SVC as PriceAnalyticsService & QuotationService
    participant DB as quotations.db
    participant CACHE as SearchCache
    participant PORTAL as Purchasing Dashboard

    Cron->>MS: POST /api/alerts/scan
    MS->>SVC: Scan active quotations against current clock (e.g. 2026-10-21)
    
    SVC->>DB: SELECT * FROM quotations WHERE status = 'ACTIVE'
    loop For each active quotation
        alt expiration_date < Today
            SVC->>DB: UPDATE quotations SET status = 'EXPIRED' WHERE id = @id
            SVC->>CACHE: Invalidate all cache entries referencing quotation_id
            SVC->>SVC: add_alert(alert_type='EXPIRING_SOON', severity='WARNING', ...)
            SVC->>DB: INSERT INTO system_alerts (alert_id, title, message, severity, ...)
        else expiration_date between Today and Today + 14 Days
            SVC->>SVC: add_alert(alert_type='EXPIRING_SOON', severity='INFO', ...)
            SVC->>DB: INSERT INTO system_alerts (...)
        end
    end

    MS-->>PORTAL: 200 OK { scanned_count: 142, expired_count: 3, alert_count: 5 }
    PORTAL->>PORTAL: Renders red alert badge on Purchasing Navigation Bar
```

---

### WF-13: 3D Flipping Employee ID Badge & 2026 Shift Calendar Navigation

The user's official MinebeaMitsumi badge features hardware-accelerated 3D CSS perspective transforms, rotating through front credentials, H1 factory calendar, and H2 factory calendar.

```mermaid
stateDiagram-v2
    [*] --> Front_Badge: Step 0 (0° Rotation)
    
    state Front_Badge {
        Official_Logo: MinebeaMitsumi Official Logo
        Emp_Photo: Employee Photo from Local Storage
        Emp_Meta: Full Name, Division, Section, Position
    }
    
    Front_Badge --> Calendar_H1: User clicks card or "พลิกบัตร" (cardStep = 1, 180° Rotation)
    
    state Calendar_H1 {
        Header_H1: 2026 Shift Calendar H1 (Jan - Jun)
        Stats_H1: 261 Working Days, 15 Traditional Holidays
        Days_H1: Shift day matrix (Bang Pa-in / Rojana schedule)
    }
    
    Calendar_H1 --> Calendar_H2: User clicks card second time (cardStep = 2, 360° Rotation)
    
    state Calendar_H2 {
        Header_H2: 2026 Shift Calendar H2 (Jul - Dec)
        Stats_H2: 104 Weekend Off-Days, Annual Shutdown
        Days_H2: Second half production shift days
    }
    
    Calendar_H2 --> Front_Badge: User clicks card third time (cardStep = 0, 540° -> 0° reset)
```

---

### WF-14: Failover, Graceful Degradation & In-Memory Offline Modes

The platform incorporates zero-crash architectural safeguards, ensuring full operational availability even during network disconnects or database maintenance.

```mermaid
flowchart TD
    REQ([Frontend Issues API Request]) --> TRY_NET{Backend Server Reachable?}
    
    TRY_NET -- Yes (:5000 Online) --> BE_MSSQL{MSSQL Host PBGM8G Connected?}
    TRY_NET -- No (Network / Server Down) --> FE_FALLBACK[Frontend In-Memory Fallback\nLocal mock accounts: X4770, A3415\nUninterrupted UI Editing]
    
    BE_MSSQL -- Yes (Pool Active) --> EXEC_SQL[Execute TDS Transactional SQL]
    BE_MSSQL -- No (Timeout / Pool Error) --> BE_FALLBACK[Backend CSV / Memory Mode\nauth.controller streams Master_Employee.csv\nrequisition.controller stores drafts in RAM]
    
    EXEC_SQL --> OK([Success 200 OK])
    BE_FALLBACK --> OK
    FE_FALLBACK --> OK
    
    subgraph Microservice_Resilience [Port 8000 AI Service Resilience]
        AI_REQ([Search / Copilot Request]) --> MS_CHK{Is Microservice Online?}
        MS_CHK -- Yes --> MS_OK[Return Semantic Results]
        MS_CHK -- No / Timeout (5000ms) --> MS_FALLBACK[AbortController aborts gracefully\nisMicroserviceOnline = false\nFriendly inline reconnection banner\nRequisition saving remains 100% active]
    end
```

---

## 3. Data State Machines & Database Lifecycle Models

### 3.1 Requisition Document State Machine

```mermaid
stateDiagram-v2
    [*] --> DRAFT: Employee creates or opens requisition form
    DRAFT --> DRAFT: Edit line items, add attachments, recalculate totals
    DRAFT --> SUBMITTED: Clicks "ส่งขออนุมัติ" (Submit Requisition)
    SUBMITTED --> IN_REVIEW: Supervisor opens document for audit
    IN_REVIEW --> APPROVED: Supervisor approves & assigns budget division
    IN_REVIEW --> REJECTED: Supervisor requests corrections (returns to DRAFT)
    REJECTED --> DRAFT: Employee modifies items & resubmits
    APPROVED --> ORDERED: Purchasing buyer executes purchase order (PO)
    ORDERED --> COMPLETED: Items received at factory tool crib / warehouse
    COMPLETED --> [*]
```

---

### 3.2 Quotation Aggregate Lifecycle

```mermaid
stateDiagram-v2
    [*] --> ACTIVE: Ingested via smart PDF extraction & verified
    ACTIVE --> EXPIRED: System clock exceeds validity_period.expiration_date
    ACTIVE --> SUPERSEDED: Newer quotation received for identical part & vendor
    EXPIRED --> ACTIVE: Purchasing buyer renews with updated validity period
    SUPERSEDED --> ARCHIVED: Preserved for 7-year statutory financial audit
    EXPIRED --> ARCHIVED: Preserved for historical price curve analytics
    ARCHIVED --> [*]
```

---

### 3.3 Manual Quotation Demand Lifecycle

```mermaid
stateDiagram-v2
    [*] --> SUBMITTED: Created via Slot-Filling Agent or Manual Request Modal
    SUBMITTED --> IN_REVIEW: Assigned to Purchasing Officer (P/H)
    IN_REVIEW --> FULFILLED: Buyer obtains quote from supplier & links QuotationId
    IN_REVIEW --> REJECTED: Obsolete part or vendor declined to quote
    FULFILLED --> [*]
    REJECTED --> [*]
```

---

### 3.4 HITL Staging Verification Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING_VERIFICATION: PDF ingested into storage/staging/
    PENDING_VERIFICATION --> PENDING_VERIFICATION: Buyer adjusts fields (Vendor, Qty, Price)
    PENDING_VERIFICATION --> VERIFIED_COMMITTED: All validation warnings resolved & committed
    PENDING_VERIFICATION --> DISCARDED: Unreadable or duplicate document rejected
    VERIFIED_COMMITTED --> [*]
    DISCARDED --> [*]
```

---

### 3.5 Database Schemas & Storage Topologies

#### MSSQL Server (`PBGM8G` / `Suppier` Database)
- **`Master_Employee`**: Central directory of all factory personnel (`Emp_No`, `Emp_Name`, `Thai_Name`, `Div_Code`, `Sec_Code`, `Process_Code`, `Position_Group`, `Shift_Group`).
- **`Requisitions`**: Document header table (`DocNumber`, `DocDate`, `EmpNo`, `Division`, `Section`, `Priority`, `TotalCost`, `Status`, `UpdatedAt`).
- **`RequisitionItems`**: Line items detail table (`Id`, `DocNumber`, `ItemNo`, `PartName`, `Spec`, `Maker`, `Vendor`, `Quantity`, `UnitPrice`, `Amount`, `AttachmentsJson`).

#### SQLite Microservice Database (`ai_quotation/quotations.db`)
- **`quotations`**: Master quotation aggregate (`quotation_id`, `vendor_name`, `issue_date`, `expiration_date`, `currency`, `total_amount`, `pdf_filename`, `pdf_sha256`, `status`).
- **`quotation_items`**: Extracted line items (`item_id`, `quotation_id`, `item_no`, `part_name`, `specification`, `quantity`, `unit_price`, `currency`).
- **`manual_quotation_requests`**: Unfulfilled demands (`request_id`, `requester_id`, `item_name`, `specification`, `urgency`, `status`, `created_at`).
- **`system_alerts`**: Event-driven notifications (`alert_id`, `alert_type`, `title`, `message`, `severity`, `related_quotation_id`, `created_at`, `is_read`).

---

## 4. Developer Implementation, Extension & Debugging Guide

### 4.1 How to Implement a New Feature End-to-End

When adding a full-stack capability (e.g., adding a new procurement approval tier):

1. **Step 1: Database Migration / Entity Definition**:
   - For relational MSSQL changes: update query definitions in [backend/controllers/requisition.controller.js](file:///d:/suppier/Suppier/backend/controllers/requisition.controller.js).
   - For AI microservice: define aggregate or value object under [ai_quotation/src/domain/](file:///d:/suppier/Suppier/ai_quotation/src/domain/).

2. **Step 2: Backend Controller & Routing**:
   - Add controller method in [backend/controllers/requisition.controller.js](file:///d:/suppier/Suppier/backend/controllers/requisition.controller.js).
   - Register REST route in [backend/routes/requisition.routes.js](file:///d:/suppier/Suppier/backend/routes/requisition.routes.js).

3. **Step 3: Frontend API Gateway Integration**:
   - Add typed method in [src/app/services/api.service.ts](file:///d:/suppier/Suppier/src/app/services/api.service.ts) wrapped with `try...catch` and fallback behavior.

4. **Step 4: Frontend Component & Template**:
   - Add reactive state variable and handler in [src/app/app.component.ts](file:///d:/suppier/Suppier/src/app/app.component.ts).
   - Bind interactive UI elements in [src/app/app.component.html](file:///d:/suppier/Suppier/src/app/app.component.html).

5. **Step 5: Automated Test Verification**:
   - Run Python test suite: `uv run pytest` in `/ai_quotation`.
   - Run Angular specs: `npm test` in project root.

---

### 4.2 Automated Testing & Validation Workflows

```bash
# ==============================================================================
# 1. AI Quotation Microservice Test Suite (Unit, Integration, RAG, Reranker)
# ==============================================================================
cd d:\suppier\Suppier\ai_quotation
.venv\Scripts\python.exe -m pytest -v

# Run targeted reranker and search fusion tests
.venv\Scripts\python.exe -m pytest tests/unit/infrastructure/test_reranker.py -v

# Run conversational slot-filling agent test
.venv\Scripts\python.exe -m pytest tests/unit/application/test_slot_filling_agent.py -v

# Run smart PDF auto-extraction heuristics test
.venv\Scripts\python.exe -m pytest tests/unit/infrastructure/test_smart_pdf_extraction.py -v

# ==============================================================================
# 2. End-to-End Playwright Automated Browser Journey
# ==============================================================================
.venv\Scripts\python.exe -m pytest tests/e2e/test_playwright_e2e.py -v

# ==============================================================================
# 3. Frontend Angular Specs
# ==============================================================================
cd d:\suppier\Suppier
npm test -- --watch=false --browsers=ChromeHeadless
```

---

### 4.3 Structured Telemetry, Logging & Coding Standards

In accordance with project governance rules:
- **Rule 1 (Transparency)**: Every API controller, service method, and search pass must log structured milestones (`[INFO]`, `[WARN]`, `[ERROR]`, `[AGENT]`).
- **Rule 2 (No Emoji)**: Plain ASCII status indicators only (`[OK]`, `[WARN]`, `[ERROR]`, `[AGENT]`). Never use graphical emojis in log outputs or commit messages to prevent Windows terminal character corruption.
- **Rule 5 (Fail-Safe Offline Mode)**: Never allow a remote database connection failure to crash the user's active session.

---

### 4.4 Troubleshooting Runbook & Known Gotchas

| Symptom | Probable Cause | Diagnostic Command & Resolution |
| :--- | :--- | :--- |
| **Port 5000 or 8000 Already in Use** | An orphaned node or python process from a prior session | Run `netstat -ano \| findstr :5000` or `:8000` in PowerShell, then terminate with `taskkill /F /PID <pid>`. Or execute `stop.bat`. |
| **HuggingFace / ONNX Model Out of Disk Space** | Models downloading to full C: drive default directory | [ai_quotation/main.py](file:///d:/suppier/Suppier/ai_quotation/main.py) explicitly redirects cache to `d:\suppier\Suppier\ai_quotation\.cache`. Verify directory exists and drive D: has sufficient free space. |
| **File Upload Truncated / HTTP 413 Error** | Express body parser payload default limit exceeded | [backend/server.js](file:///d:/suppier/Suppier/backend/server.js) sets `express.json({ limit: '50mb' })`. Ensure large attachments do not exceed 50MB. |
| **Microservice Shows Offline in UI** | FastAPI process not started or Python venv missing | Run `.venv\Scripts\python.exe main.py` manually in `ai_quotation/` to observe terminal startup diagnostics. |
| **Thai Buddhist Era Date Error in Requisition** | Vendor PDF quotes dated `2569` causing invalid ISO date | [pdf_reader.py](file:///d:/suppier/Suppier/ai_quotation/src/infrastructure/pdf_reader.py) automatically converts years $> 2400$ by subtracting 543. If a new vendor format is introduced, verify regex pattern in `_parse_date_heurstic()`. |
