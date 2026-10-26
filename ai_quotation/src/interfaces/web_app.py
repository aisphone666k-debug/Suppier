from datetime import date, datetime
import hashlib
import os
import shutil
import sqlite3
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from src.domain.quotation import (
    QuotationId,
    QuotationStatus,
    QuotationExpiredException,
    InvalidQuotationStateException,
)
from src.domain.validity_period import InvalidValidityPeriodException
from src.domain.manual_quotation_request import RequestUrgency, InvalidRequestStateException
from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.infrastructure.search_cache import MemorySearchCache
from src.infrastructure.vector_index import MemoryVectorIndex
from src.infrastructure.embedding_engine import FastEmbedEngine
from src.infrastructure.pdf_reader import PdfDocumentReader, CorruptPdfDocumentException
from src.application.quotation_service import QuotationApplicationService
from src.application.quotation_inquiry_service import QuotationInquiryService
from src.infrastructure.gemini_answer_generator import GeminiAnswerGenerator, GeminiApiException
from src.infrastructure.google_drive_importer import GoogleDriveImporter, GoogleDriveImportError


def seed_existing_quotations(service: QuotationApplicationService, sample_dir: str = "quoatation") -> int:
    """Auto-seeds existing PDF quotation samples from quoatation/ into the system using intelligent extraction."""
    if not os.path.exists(sample_dir):
        return 0

    reader = PdfDocumentReader()
    seeded_count = 0
    today = date.today()

    for filename in os.listdir(sample_dir):
        if not filename.lower().endswith(".pdf"):
            continue
        file_path = os.path.join(sample_dir, filename)
        try:
            draft = reader.extract_draft(file_path)
            q_num = draft.quotation_number or os.path.splitext(filename)[0]
            vendor = draft.vendor_name or "Vendor International"
            issue_date = draft.issue_date or today
            expiration_date = draft.expiration_date or date(today.year, 12, 31)

            # Build line items from extracted draft
            if draft.items:
                items = []
                for it in draft.items:
                    desc = it.description
                    if "bando" in filename.lower() and "transmission" not in desc.lower():
                        desc = f"Bando Industrial Transmission V-Belt - {desc}".strip()
                    items.append({
                        "item_number": it.item_number,
                        "part_number": it.part_number,
                        "description": desc,
                        "quantity": it.quantity,
                        "unit": it.unit,
                        "unit_price": it.unit_price,
                    })
            else:
                clean_item_desc = os.path.splitext(filename)[0]
                items = [
                    {
                        "item_number": 1,
                        "part_number": q_num,
                        "description": f"{clean_item_desc} - Commercial Vendor Supply",
                        "quantity": 1.0,
                        "unit": "Lot",
                        "unit_price": draft.total_amount or 1500.0,
                    }
                ]

            service.register_quotation(
                quotation_number=q_num,
                vendor_name=vendor,
                issue_date=issue_date,
                expiration_date=expiration_date,
                items=items,
                pdf_path=file_path,
                pdf_sha256=draft.sha256,
                user_role="PH_USER",
                raw_text=draft.raw_text,
                currency=draft.currency,
                vendor_tax_id=draft.vendor_tax_id,
            )
            seeded_count += 1
        except Exception as e:
            print(f"[WARN] Failed to auto-seed {filename}: {e}")

    return seeded_count


class BatchCommitItem(BaseModel):
    item_number: Optional[int] = 1
    part_number: Optional[str] = None
    description: str
    quantity: Optional[float] = 1.0
    unit: Optional[str] = "Pcs"
    unit_price: Optional[float] = 0.0


class BatchCommitQuotation(BaseModel):
    staging_id: Optional[str] = None
    temp_file_path: Optional[str] = None
    filename: str
    quotation_number: str
    vendor_name: str
    vendor_tax_id: Optional[str] = ""
    issue_date: str
    expiration_date: str
    currency: Optional[str] = "THB"
    items: list[BatchCommitItem] = Field(default_factory=list)


class BatchCommitRequest(BaseModel):
    user_role: str = "PH_USER"
    quotations: list[BatchCommitQuotation]


class GoogleDriveImportRequest(BaseModel):
    user_role: str = "PH_USER"
    url: Optional[str] = None
    urls: Optional[list[str]] = None
    raw_text: Optional[str] = None


def create_app(db_path: str = "quotations.db", auto_seed: bool = True) -> FastAPI:
    app = FastAPI(title="QuotationFinder Engine", version="1.0.0")

    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
    templates = Jinja2Templates(directory=templates_dir)

    # Initialize persistence & services
    conn = sqlite3.connect(db_path, check_same_thread=False)
    quotation_repo = SqliteQuotationRepository(conn)
    quotation_repo.initialize_schema()

    manual_repo = SqliteManualRequestRepository(conn)
    manual_repo.initialize_schema()

    cache = MemorySearchCache(ttl_seconds=1800)
    vector_index = MemoryVectorIndex()
    embedding_engine = FastEmbedEngine()

    service = QuotationApplicationService(
        quotation_repository=quotation_repo,
        manual_request_repository=manual_repo,
        search_cache=cache,
        vector_index=vector_index,
        embedding_engine=embedding_engine,
    )

    if auto_seed and len(quotation_repo.find_all()) == 0:
        seed_existing_quotations(service)

    # Ensure in-memory vector index is populated from SQLite
    service.reindex_all()

    # Initialize RAG answer generator
    try:
        generator = GeminiAnswerGenerator()
    except Exception:
        from src.application.inquiry_generator import AnswerGeneratorPort
        class MissingKeyGenerator(AnswerGeneratorPort):
            def generate_answer(self, query, context_chunks):
                return "Gemini API key is not configured. Please add GEMINI_API_KEY in credentials.ini."
        generator = MissingKeyGenerator()

    inquiry_service = QuotationInquiryService(
        quotation_service=service,
        answer_generator=generator,
    )

    app.state.service = service
    app.state.inquiry_service = inquiry_service
    app.state.templates = templates


    # --- HTTP Routes ---

    @app.post("/api/inquiry/ask", response_class=HTMLResponse)
    async def ask_inquiry(
        query: str = Form(...),
        user_role: str = Form("NORMAL_USER"),
    ):
        today = date.today()
        try:
            res = app.state.inquiry_service.answer_inquiry_with_telemetry(
                query=query,
                user_role=user_role,
                reference_date=today,
            )
            badge_html = (
                f'<span class="text-[10px] bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded-full border border-emerald-300 ml-auto">[CACHED] ({res.total_duration_ms}ms)</span>'
                if res.cached
                else f'<span class="text-[10px] bg-indigo-100 text-indigo-800 font-semibold px-2 py-0.5 rounded-full border border-indigo-200 ml-auto">Gemini 2.5 Flash ({res.total_duration_ms}ms)</span>'
            )

            citations_html = ""
            if res.citations:
                lines_html = []
                for cit in res.citations:
                    status_badge = (
                        '<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-emerald-100 text-emerald-800">ACTIVE</span>'
                        if cit.status == "ACTIVE"
                        else '<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-rose-100 text-rose-800">EXPIRED</span>'
                    )
                    safe_query = cit.search_query.replace("'", "\\'")
                    lines_html.append(f"""
                        <div class="flex items-center justify-between bg-white border border-indigo-100 rounded-xl p-2.5 hover:border-indigo-300 hover:shadow-xs transition-all">
                            <div class="min-w-0 flex-1 pr-3">
                                <div class="flex items-center space-x-2">
                                    <span class="font-bold text-slate-900 text-xs font-mono">{cit.quotation_number}</span>
                                    <span class="text-slate-400 text-xs">&bull;</span>
                                    <span class="text-xs text-slate-700 font-medium truncate">{cit.vendor_name}</span>
                                    {status_badge}
                                </div>
                                <div class="text-[11px] text-slate-500 truncate mt-0.5">
                                    <span>{cit.items_summary}</span>
                                    <span class="text-slate-400 font-semibold ml-1">&bull; {cit.price_summary}</span>
                                </div>
                            </div>
                            <div class="flex items-center space-x-1.5 flex-shrink-0">
                                <button type="button"
                                        onclick="setQuery('{safe_query}')"
                                        title="Research this item in traditional search engine"
                                        class="px-2.5 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors flex items-center">
                                    <svg class="w-3.5 h-3.5 mr-1 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                    </svg>
                                    Research
                                </button>
                                <button type="button"
                                        hx-get="/pdf-modal/{cit.quotation_id}"
                                        hx-target="#modal-container"
                                        title="Review source PDF quotation"
                                        class="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg transition-colors flex items-center">
                                    <svg class="w-3.5 h-3.5 mr-1 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                                    </svg>
                                    PDF
                                </button>
                            </div>
                        </div>
                    """)
                joined_lines = "".join(lines_html)
                citations_html = f"""
                    <div class="mt-4 pt-3 border-t border-indigo-200/60">
                        <div class="text-[11px] font-bold uppercase tracking-wider text-indigo-900 mb-2 flex items-center justify-between">
                            <span>Referenced Quotations (Interactive Citations &amp; Research)</span>
                            <span class="text-[10px] text-slate-500 font-normal">Click [Research] to explore in search engine or [PDF] to inspect original</span>
                        </div>
                        <div class="space-y-1.5">
                            {joined_lines}
                        </div>
                    </div>
                """

            return HTMLResponse(f"""
                <div class="bg-indigo-50/70 border border-indigo-200 rounded-2xl p-5 shadow-sm text-slate-800 text-sm animate-in fade-in duration-150">
                    <div class="flex items-center space-x-2 text-indigo-700 font-bold mb-2">
                        <svg class="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                        <span>AI Procurement Assistant (RAG Grounded)</span>
                        {badge_html}
                    </div>
                    <div class="prose prose-sm max-w-none text-slate-700 leading-relaxed whitespace-pre-line">
                        {res.answer}
                    </div>
                    {citations_html}
                </div>
            """)
        except GeminiApiException as e:
            return HTMLResponse(f"""
                <div class="bg-amber-50 border border-amber-200 rounded-2xl p-5 shadow-sm text-amber-900 text-sm">
                    <div class="flex items-center space-x-2 font-bold mb-2 text-amber-800">
                        <svg class="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                        </svg>
                        <span>Gemini API Notice</span>
                    </div>
                    <p class="text-xs text-amber-700 leading-relaxed mb-3">{e}</p>
                    <p class="text-[11px] text-amber-600">Tip: Ensure Gemini API is enabled in your Google Cloud Console or generate an API key via <a href="https://aistudio.google.com/app/apikey" target="_blank" class="underline font-semibold">Google AI Studio</a>.</p>
                </div>
            """)

    @app.post("/api/inquiry/ask-json")
    async def ask_inquiry_json(
        query: str = Form(...),
        user_role: str = Form("NORMAL_USER"),
    ):
        today = date.today()
        try:
            res = app.state.inquiry_service.answer_inquiry_with_telemetry(
                query=query,
                user_role=user_role,
                reference_date=today,
            )
            return {
                "answer": res.answer,
                "cached": res.cached,
                "total_duration_ms": res.total_duration_ms,
                "citations": [
                    {
                        "quotation_id": cit.quotation_id,
                        "quotation_number": cit.quotation_number,
                        "vendor_name": cit.vendor_name,
                        "status": cit.status,
                        "items_summary": cit.items_summary,
                        "price_summary": cit.price_summary,
                        "search_query": cit.search_query,
                    }
                    for cit in res.citations
                ],
            }
        except Exception as e:
            return {"answer": f"Error: {e}", "cached": False, "total_duration_ms": 0, "citations": []}

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="search.html",
            context={"query": "", "results": None},
        )

    @app.post("/search", response_class=HTMLResponse)
    async def search(
        request: Request,
        query: str = Form(""),
        user_role: str = Form("NORMAL_USER"),
    ):
        today = date.today()
        results = service.search(
            query=query,
            user_role=user_role,
            reference_date=today,
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/search_results.html",
            context={"query": query.strip(), "results": results, "user_role": user_role},
        )

    @app.get("/api/search")
    async def api_search(
        query: str = "",
        user_role: str = "NORMAL_USER",
    ):
        today = date.today()
        results = service.search(
            query=query,
            user_role=user_role,
            reference_date=today,
        )
        return {
            "query": query.strip(),
            "count": len(results),
            "results": [
                {
                    "quotation_id": str(r.quotation.quotation_id),
                    "quotation_number": r.quotation.quotation_number,
                    "vendor_name": r.quotation.vendor_name,
                    "vendor_tax_id": r.quotation.vendor_tax_id,
                    "currency": r.quotation.currency,
                    "status": r.quotation.status.value,
                    "issue_date": r.quotation.validity_period.issue_date.isoformat(),
                    "expiration_date": r.quotation.validity_period.expiration_date.isoformat(),
                    "confidence_score": float(r.confidence.value),
                    "can_receive": r.can_receive,
                    "pdf_url": f"/pdf/{os.path.basename(r.quotation.pdf_path)}",
                    "items": [
                        {
                            "item_number": it.item_number,
                            "part_number": it.part_number,
                            "description": it.description,
                            "quantity": it.quantity,
                            "unit": it.unit,
                            "unit_price": it.unit_price,
                            "total_price": it.total_price,
                        }
                        for it in r.quotation.items
                    ],
                }
                for r in results
            ],
        }


    @app.get("/pdf/{filename}")
    async def serve_pdf(filename: str):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Look in quoatation/ or storage/pdf/
        candidates = [
            os.path.join(base_dir, "quoatation", filename),
            os.path.join(base_dir, "storage", "pdf", filename),
            os.path.join("quoatation", filename),
            os.path.join("storage", "pdf", filename),
            filename,
        ]
        for c in candidates:
            if os.path.exists(c):
                return FileResponse(c, media_type="application/pdf")
        raise HTTPException(status_code=404, detail="PDF file not found")

    @app.get("/pdf-modal/{quotation_id}", response_class=HTMLResponse)
    async def pdf_modal(request: Request, quotation_id: str):
        q = service.quotation_repository.find_by_id(QuotationId(quotation_id))
        if not q:
            raise HTTPException(status_code=404, detail="Quotation not found")
        pdf_filename = os.path.basename(q.pdf_path)
        return templates.TemplateResponse(
            request=request,
            name="partials/pdf_modal.html",
            context={"quotation": q, "pdf_filename": pdf_filename},
        )


    @app.get("/manual-request-modal", response_class=HTMLResponse)
    async def manual_request_modal(request: Request, prefill: str = ""):
        return templates.TemplateResponse(
            request=request,
            name="partials/manual_request_modal.html",
            context={"prefill": prefill},
        )

    @app.post("/api/requests/manual", response_class=HTMLResponse)
    async def submit_manual_request(
        request: Request,
        item_description: str = Form(...),
        department: str = Form(...),
        part_number: Optional[str] = Form(None),
        target_quantity: Optional[float] = Form(1.0),
        target_unit: Optional[str] = Form("Pcs"),
        needed_by_date: Optional[str] = Form(None),
        urgency: str = Form("NORMAL"),
        requester_user_id: str = Form("emp_user"),
    ):
        if not item_description or not item_description.strip():
            raise HTTPException(status_code=400, detail="Item description cannot be empty")
        if target_quantity is not None and target_quantity <= 0:
            raise HTTPException(status_code=400, detail="Target quantity must be strictly positive")

        needed_date = None
        if needed_by_date and needed_by_date.strip():
            try:
                needed_date = date.fromisoformat(needed_by_date.strip())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid needed-by date format")

        try:
            req = service.submit_manual_request(
                requester_user_id=requester_user_id,
                department=department,
                item_description=item_description.strip(),
                part_number=part_number.strip() if part_number else None,
                target_quantity=target_quantity,
                target_unit=target_unit,
                needed_by_date=needed_date,
                urgency=RequestUrgency(urgency),
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return HTMLResponse(f"""
            <div class="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
                <div class="bg-white rounded-2xl p-6 max-w-md w-full text-center shadow-2xl">
                    <div class="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-900 mb-1">Request Submitted Successfully</h3>
                    <p class="text-sm text-slate-500 mb-4">Your demand has been sent to Purchasing Hub under Ticket ID <span class="font-mono font-bold text-indigo-600">{req.ticket_id}</span>.</p>
                    <button onclick="document.getElementById('modal-container').innerHTML = ''" class="px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700">Close</button>
                </div>
            </div>
        """)

    @app.post("/api/quotations/{quotation_id}/receive")
    async def receive_quotation(quotation_id: str, user_id: str = Form("current_user")):
        today = date.today()
        try:
            ack = service.acknowledge_quotation(
                quotation_id=QuotationId(quotation_id),
                user_id=user_id,
                reference_date=today,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Quotation {quotation_id} not found")
        except QuotationExpiredException:
            return HTMLResponse(
                f"""
                <span class="inline-flex items-center px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-100 text-rose-800 border border-rose-300">
                    [ERROR] Quotation has expired and cannot be received
                </span>
                """,
                status_code=400,
            )
        except InvalidQuotationStateException:
            return HTMLResponse(
                f"""
                <span class="inline-flex items-center px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-100 text-amber-800 border border-amber-300">
                    [WARN] Quotation cannot be received in current state
                </span>
                """,
                status_code=400,
            )

        return HTMLResponse(f"""
            <button disabled class="inline-flex items-center px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-300">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Successfully Received ({ack.received_date})
            </button>
        """)

    @app.get("/ph-portal", response_class=HTMLResponse)
    async def ph_portal(request: Request):
        today = date.today()
        all_q = service.list_all_quotations()
        for q in all_q:
            q.evaluate_expiration(today)
        active_q = [q for q in all_q if q.status == QuotationStatus.ACTIVE]
        expired_q = [q for q in all_q if q.status == QuotationStatus.EXPIRED]
        pending_reqs = service.list_pending_manual_requests()

        return templates.TemplateResponse(
            request=request,
            name="ph_portal.html",
            context={
                "active_quotations": active_q,
                "expired_quotations": expired_q,
                "pending_requests": pending_reqs,
            },
        )


    @app.post("/api/quotations/{quotation_id}/renew", response_class=HTMLResponse)
    async def renew_quotation(
        quotation_id: str,
        new_expiration_date: str = Form(...),
        remarks: str = Form(""),
        user_role: str = Form("PH_USER"),
    ):
        if user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users are authorized to renew quotations")

        try:
            new_date = date.fromisoformat(new_expiration_date.strip())
        except (ValueError, AttributeError):
            return HTMLResponse(
                f"""
                <tr id="row-{quotation_id}" class="bg-rose-50/50">
                    <td colspan="5" class="px-4 py-3 text-rose-600 font-semibold text-xs">
                        [ERROR] Invalid date format for expiration date.
                    </td>
                </tr>
                """,
                status_code=400,
            )

        today = date.today()
        try:
            renewed = service.renew_quotation(
                quotation_id=QuotationId(quotation_id),
                new_expiration_date=new_date,
                user_role=user_role,
                reference_date=today,
                remarks=remarks,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Quotation {quotation_id} not found")
        except InvalidValidityPeriodException:
            return HTMLResponse(
                f"""
                <tr id="row-{quotation_id}" class="bg-rose-50/50">
                    <td colspan="5" class="px-4 py-3 text-rose-600 font-semibold text-xs">
                        [ERROR] Invalid validity period: renewal date must be strictly in the future.
                    </td>
                </tr>
                """,
                status_code=400,
            )

        return HTMLResponse(f"""
            <tr id="row-{quotation_id}" class="bg-emerald-50/50">
                <td class="px-4 py-3 font-bold text-slate-900">{renewed.quotation_number}</td>
                <td class="px-4 py-3 text-slate-600">{renewed.vendor_name}</td>
                <td class="px-4 py-3 text-slate-600">Renewed successfully!</td>
                <td class="px-4 py-3">
                    <span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">
                        ACTIVE until {renewed.validity_period.expiration_date}
                    </span>
                </td>
                <td class="px-4 py-3 text-right">
                    <span class="text-xs font-semibold text-emerald-600">[OK] Renewed</span>
                </td>
            </tr>
        """)

    @app.post("/api/quotations/extract-preview")
    async def extract_preview_endpoint(
        pdf_file: UploadFile = File(...),
        user_role: str = Form("PH_USER"),
    ):
        if user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can extract previews")

        os.makedirs("storage/staging", exist_ok=True)
        temp_path = os.path.join("storage", "staging", f"stage_{uuid.uuid4().hex}_{pdf_file.filename}")
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(pdf_file.file, buffer)
            draft = service.extract_draft_from_pdf(temp_path, user_role=user_role)
        except (CorruptPdfDocumentException, Exception) as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF document: {e}")

        items_list = [
            {
                "item_number": it.item_number,
                "description": it.description,
                "part_number": it.part_number,
                "quantity": it.quantity,
                "unit": it.unit,
                "unit_price": it.unit_price,
                "amount": it.amount,
            }
            for it in draft.items
        ]

        first_item = items_list[0] if items_list else {
            "item_number": 1,
            "description": "General Industrial Item",
            "part_number": None,
            "quantity": 1.0,
            "unit": "Pcs",
            "unit_price": 0.0,
            "amount": 0.0,
        }

        from fastapi.responses import JSONResponse
        return JSONResponse({
            "quotation_number": draft.quotation_number,
            "vendor_name": draft.vendor_name,
            "vendor_tax_id": draft.vendor_tax_id,
            "issue_date": draft.issue_date.isoformat(),
            "expiration_date": draft.expiration_date.isoformat(),
            "currency": draft.currency,
            "total_amount": draft.total_amount,
            "items": items_list,
            "first_item": first_item,
        })

    @app.post("/api/quotations/register")
    async def register_quotation_endpoint(
        request: Request,
        pdf_file: UploadFile = File(...),
        quotation_number: Optional[str] = Form(None),
        vendor_name: Optional[str] = Form(None),
        issue_date: Optional[str] = Form(None),
        expiration_date: Optional[str] = Form(None),
        item_description: Optional[str] = Form(None),
        item_part_number: Optional[str] = Form(None),
        item_quantity: Optional[float] = Form(None),
        item_unit: Optional[str] = Form(None),
        item_unit_price: Optional[float] = Form(None),
        items_json: Optional[str] = Form(None),
        currency: Optional[str] = Form(None),
        user_role: str = Form("PH_USER"),
    ):
        if user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can register quotations")

        os.makedirs("storage/pdf", exist_ok=True)
        saved_pdf_path = os.path.join("storage", "pdf", pdf_file.filename)
        try:
            with open(saved_pdf_path, "wb") as buffer:
                shutil.copyfileobj(pdf_file.file, buffer)

            reader = PdfDocumentReader()
            draft = reader.extract_draft(saved_pdf_path)
        except (CorruptPdfDocumentException, Exception) as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF document: {e}")

        try:
            final_issue_date = date.fromisoformat(issue_date.strip()) if (issue_date and issue_date.strip()) else draft.issue_date
            final_expiration_date = date.fromisoformat(expiration_date.strip()) if (expiration_date and expiration_date.strip()) else draft.expiration_date
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

        final_quotation_number = quotation_number.strip() if (quotation_number and quotation_number.strip()) else draft.quotation_number
        final_vendor_name = vendor_name.strip() if (vendor_name and vendor_name.strip()) else draft.vendor_name
        final_currency = currency.strip() if (currency and currency.strip()) else draft.currency

        # 1. First priority: items_json from the interactive items editor
        parsed_custom_items = None
        if items_json and items_json.strip():
            import json
            try:
                raw_parsed = json.loads(items_json.strip())
                if isinstance(raw_parsed, list) and len(raw_parsed) > 0:
                    valid_items = [
                        {
                            "item_number": it.get("item_number", idx + 1),
                            "part_number": it.get("part_number") or None,
                            "description": it.get("description", "").strip(),
                            "quantity": float(it.get("quantity", 1.0)),
                            "unit": it.get("unit", "Pcs") or "Pcs",
                            "unit_price": float(it.get("unit_price", 0.0)),
                        }
                        for idx, it in enumerate(raw_parsed)
                        if it.get("description", "").strip()
                    ]
                    if valid_items:
                        parsed_custom_items = valid_items
            except Exception as e:
                print(f"[WARN] Failed to parse items_json: {e}")

        if parsed_custom_items:
            items = parsed_custom_items
        elif draft.items and len(draft.items) > 1:
            items = []
            for idx, it in enumerate(draft.items):
                if idx == 0 and item_description and item_description.strip():
                    items.append({
                        "item_number": it.item_number,
                        "part_number": item_part_number if item_part_number else it.part_number,
                        "description": item_description.strip(),
                        "quantity": item_quantity if item_quantity is not None else it.quantity,
                        "unit": item_unit or it.unit,
                        "unit_price": item_unit_price if item_unit_price is not None else it.unit_price,
                    })
                else:
                    items.append({
                        "item_number": it.item_number,
                        "part_number": it.part_number,
                        "description": it.description,
                        "quantity": it.quantity,
                        "unit": it.unit,
                        "unit_price": it.unit_price,
                    })
        elif item_description and item_description.strip():
            items = [
                {
                    "item_number": 1,
                    "part_number": item_part_number,
                    "description": item_description.strip(),
                    "quantity": item_quantity if item_quantity is not None else 1.0,
                    "unit": item_unit or "Pcs",
                    "unit_price": item_unit_price if item_unit_price is not None else (draft.total_amount or 0.0),
                }
            ]
        elif draft.items:
            items = [
                {
                    "item_number": it.item_number,
                    "part_number": it.part_number,
                    "description": it.description,
                    "quantity": it.quantity,
                    "unit": it.unit,
                    "unit_price": it.unit_price,
                }
                for it in draft.items
            ]
        else:
            items = [
                {
                    "item_number": 1,
                    "part_number": None,
                    "description": "General Quotation Item",
                    "quantity": 1.0,
                    "unit": "Pcs",
                    "unit_price": draft.total_amount or 0.0,
                }
            ]

        try:
            service.register_quotation(
                quotation_number=final_quotation_number,
                vendor_name=final_vendor_name,
                issue_date=final_issue_date,
                expiration_date=final_expiration_date,
                items=items,
                pdf_path=saved_pdf_path,
                pdf_sha256=draft.sha256,
                user_role=user_role,
                currency=final_currency,
                vendor_tax_id=draft.vendor_tax_id,
                raw_text=draft.raw_text,
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Only PH Users can register quotations")
        except InvalidValidityPeriodException as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/ph-portal", status_code=303)

    @app.post("/api/requests/{ticket_id}/fulfill", response_class=HTMLResponse)
    async def fulfill_request(
        ticket_id: str,
        quotation_id: str = Form(...),
        user_role: str = Form("PH_USER"),
    ):
        if user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can fulfill manual requests")

        try:
            service.fulfill_manual_request(
                ticket_id=ticket_id,
                quotation_id=QuotationId(quotation_id.strip()),
                ph_user_id="ph_admin",
                user_role=user_role,
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (InvalidRequestStateException, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        return HTMLResponse(f"""
            <tr id="req-row-{ticket_id}" class="bg-emerald-50/50">
                <td class="px-4 py-3 font-mono font-bold text-slate-900">{ticket_id}</td>
                <td colspan="3" class="px-4 py-3 text-emerald-800 text-xs font-semibold">
                    Fulfilled with quotation {quotation_id}
                </td>
                <td class="px-4 py-3 text-right">
                    <span class="text-xs font-semibold text-emerald-600">[OK] Closed</span>
                </td>
            </tr>
        """)

    @app.post("/api/quotations/batch-register")
    async def batch_register_endpoint(
        pdf_files: list[UploadFile] = File(...),
        user_role: str = Form("PH_USER"),
    ):
        if user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can register quotations")

        reader = PdfDocumentReader()
        results = []
        os.makedirs("storage/pdf", exist_ok=True)
        today = date.today()

        for pdf_file in pdf_files:
            filename = pdf_file.filename
            if not filename or not filename.lower().endswith(".pdf"):
                continue

            saved_pdf_path = os.path.join("storage", "pdf", filename)
            try:
                with open(saved_pdf_path, "wb") as buffer:
                    shutil.copyfileobj(pdf_file.file, buffer)

                draft = reader.extract_draft(saved_pdf_path)
                q_num = draft.quotation_number or os.path.splitext(filename)[0]
                vendor = draft.vendor_name or "Vendor International"
                issue_date = draft.issue_date or today
                expiration_date = draft.expiration_date or date(today.year, 12, 31)

                if draft.items:
                    items = [
                        {
                            "item_number": it.item_number,
                            "part_number": it.part_number,
                            "description": it.description,
                            "quantity": it.quantity,
                            "unit": it.unit,
                            "unit_price": it.unit_price,
                        }
                        for it in draft.items
                    ]
                else:
                    clean_item_desc = os.path.splitext(filename)[0]
                    items = [
                        {
                            "item_number": 1,
                            "part_number": q_num,
                            "description": f"{clean_item_desc} - Commercial Vendor Supply",
                            "quantity": 1.0,
                            "unit": "Lot",
                            "unit_price": draft.total_amount or 1500.0,
                        }
                    ]

                service.register_quotation(
                    quotation_number=q_num,
                    vendor_name=vendor,
                    issue_date=issue_date,
                    expiration_date=expiration_date,
                    items=items,
                    pdf_path=saved_pdf_path,
                    pdf_sha256=draft.sha256,
                    user_role=user_role,
                    currency=draft.currency,
                    vendor_tax_id=draft.vendor_tax_id,
                    raw_text=draft.raw_text,
                )

                results.append({
                    "filename": filename,
                    "quotation_number": q_num,
                    "vendor_name": vendor,
                    "items_count": len(items),
                    "total_amount": draft.total_amount,
                    "currency": draft.currency,
                    "issue_date": str(issue_date),
                    "expiration_date": str(expiration_date),
                    "status": "SUCCESS",
                })
            except Exception as e:
                results.append({
                    "filename": filename,
                    "quotation_number": os.path.splitext(filename)[0],
                    "vendor_name": "Unknown",
                    "items_count": 0,
                    "status": "ERROR",
                    "error": str(e),
                })

        return {
            "total_files": len(pdf_files),
            "successful": sum(1 for r in results if r["status"] == "SUCCESS"),
            "failed": sum(1 for r in results if r["status"] == "ERROR"),
            "results": results,
        }

    @app.post("/api/quotations/batch-preview")
    async def batch_preview_endpoint(
        pdf_files: list[UploadFile] = File(...),
        user_role: str = Form("PH_USER"),
    ):
        if user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can extract previews")

        reader = PdfDocumentReader()
        drafts = []
        os.makedirs("storage/staging", exist_ok=True)
        today = date.today()

        for pdf_file in pdf_files:
            filename = pdf_file.filename
            if not filename or not filename.lower().endswith(".pdf"):
                continue

            unique_prefix = uuid.uuid4().hex[:8]
            temp_filename = f"stage_{unique_prefix}_{filename}"
            temp_path = os.path.join("storage", "staging", temp_filename)

            try:
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(pdf_file.file, buffer)

                draft = reader.extract_draft(temp_path)
                q_num = draft.quotation_number or os.path.splitext(filename)[0]
                vendor = draft.vendor_name or "Vendor International"
                issue_date = draft.issue_date or today
                expiration_date = draft.expiration_date or date(today.year, 12, 31)

                if draft.items:
                    items = [
                        {
                            "item_number": it.item_number,
                            "part_number": it.part_number or "",
                            "description": it.description or "Industrial Item",
                            "quantity": float(it.quantity or 1.0),
                            "unit": it.unit or "Pcs",
                            "unit_price": float(it.unit_price or 0.0),
                            "total_price": float(it.amount if it.amount is not None else (it.quantity * it.unit_price if it.quantity and it.unit_price else 0.0)),
                        }
                        for it in draft.items
                    ]
                else:
                    clean_item_desc = os.path.splitext(filename)[0]
                    items = [
                        {
                            "item_number": 1,
                            "part_number": q_num,
                            "description": f"{clean_item_desc} - Commercial Vendor Supply",
                            "quantity": 1.0,
                            "unit": "Lot",
                            "unit_price": float(draft.total_amount or 1500.0),
                            "total_price": float(draft.total_amount or 1500.0),
                        }
                    ]

                total_amount = float(draft.total_amount) if draft.total_amount is not None else sum(it["total_price"] for it in items)

                drafts.append({
                    "staging_id": f"stage_{unique_prefix}",
                    "temp_file_path": temp_path.replace("\\", "/"),
                    "filename": filename,
                    "quotation_number": q_num,
                    "vendor_name": vendor,
                    "vendor_tax_id": draft.vendor_tax_id or "",
                    "issue_date": str(issue_date),
                    "expiration_date": str(expiration_date),
                    "currency": draft.currency or "THB",
                    "total_amount": round(total_amount, 2),
                    "items": items,
                })
            except Exception as e:
                drafts.append({
                    "staging_id": f"stage_{unique_prefix}",
                    "temp_file_path": temp_path.replace("\\", "/"),
                    "filename": filename,
                    "quotation_number": os.path.splitext(filename)[0],
                    "vendor_name": "Unknown Vendor",
                    "vendor_tax_id": "",
                    "issue_date": str(today),
                    "expiration_date": str(date(today.year, 12, 31)),
                    "currency": "THB",
                    "total_amount": 0.0,
                    "items": [
                        {
                            "item_number": 1,
                            "part_number": "",
                            "description": f"Extracted item from {filename}",
                            "quantity": 1.0,
                            "unit": "Pcs",
                            "unit_price": 0.0,
                            "total_price": 0.0,
                        }
                    ],
                    "warning": str(e),
                })

        return {
            "total_files": len(pdf_files),
            "drafts": drafts,
        }

    @app.post("/api/quotations/gdrive-import")
    async def gdrive_import_endpoint(payload: GoogleDriveImportRequest):
        if payload.user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can import from Google Drive")

        text_inputs = []
        if payload.url:
            text_inputs.append(payload.url)
        if payload.urls:
            text_inputs.extend(payload.urls)
        if payload.raw_text:
            text_inputs.append(payload.raw_text)

        combined_text = "\n".join(text_inputs).strip()
        if not combined_text:
            raise HTTPException(
                status_code=400,
                detail="ไม่พบข้อมูลหรือลิงก์ Google Drive โปรดระบุลิงก์ เช่น https://drive.google.com/file/d/..."
            )

        targets = GoogleDriveImporter.extract_gdrive_targets(combined_text)
        if not targets:
            raise HTTPException(
                status_code=400,
                detail="ไม่พบลิงก์ Google Drive ในข้อมูลที่ส่งมา โปรดคัดลอกลิงก์จาก Google Drive เช่น https://drive.google.com/file/d/..."
            )

        # Expand folders into individual files if public
        file_targets = []
        folder_targets = []
        for t in targets:
            if t["type"] == "folder":
                folder_targets.append(t)
                folder_file_ids = GoogleDriveImporter.fetch_folder_file_ids(t["id"])
                if folder_file_ids:
                    for fid in folder_file_ids:
                        file_targets.append({"type": "file", "id": fid, "source": f"folder:{t['id']}"})
            else:
                file_targets.append(t)

        if not file_targets:
            if folder_targets:
                raise HTTPException(
                    status_code=400,
                    detail="ไม่สามารถดึงรายการไฟล์จากโฟลเดอร์ Google Drive นี้ได้: โปรดตรวจสอบว่าโฟลเดอร์ได้ตั้งค่าการแชร์เป็น 'ทุกคนที่มีลิงก์ (Anyone with the link)' หรือเปิดเข้าไปในโฟลเดอร์แล้วคัดลอกลิงก์ของไฟล์ PDF โดยตรง (เช่น https://drive.google.com/file/d/...)"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="ไม่พบไฟล์ที่สามารถดาวน์โหลดได้จากลิงก์ Google Drive ที่ระบุ"
                )

        reader = PdfDocumentReader()
        drafts = []
        os.makedirs("storage/staging", exist_ok=True)
        today = date.today()

        for t in file_targets:
            item_id = t["id"]
            item_type = t.get("type", "file")
            unique_prefix = uuid.uuid4().hex[:8]

            try:
                temp_path, filename = GoogleDriveImporter.download_gdrive_pdf(
                    item_id=item_id,
                    item_type=item_type,
                    dest_dir=os.path.join("storage", "staging")
                )

                draft = reader.extract_draft(temp_path)
                q_num = draft.quotation_number or os.path.splitext(filename)[0]
                vendor = draft.vendor_name or "Vendor International"
                issue_date = draft.issue_date or today
                expiration_date = draft.expiration_date or date(today.year, 12, 31)

                if draft.items:
                    items = [
                        {
                            "item_number": it.item_number,
                            "part_number": it.part_number or "",
                            "description": it.description or "Industrial Item",
                            "quantity": float(it.quantity or 1.0),
                            "unit": it.unit or "Pcs",
                            "unit_price": float(it.unit_price or 0.0),
                            "total_price": float(it.amount if it.amount is not None else (it.quantity * it.unit_price if it.quantity and it.unit_price else 0.0)),
                        }
                        for it in draft.items
                    ]
                else:
                    clean_item_desc = os.path.splitext(filename)[0]
                    items = [
                        {
                            "item_number": 1,
                            "part_number": q_num,
                            "description": f"{clean_item_desc} - Google Drive Supply",
                            "quantity": 1.0,
                            "unit": "Lot",
                            "unit_price": float(draft.total_amount or 1500.0),
                            "total_price": float(draft.total_amount or 1500.0),
                        }
                    ]

                total_amount = float(draft.total_amount) if draft.total_amount is not None else sum(it["total_price"] for it in items)

                drafts.append({
                    "staging_id": f"stage_{unique_prefix}",
                    "temp_file_path": temp_path.replace("\\", "/"),
                    "filename": filename,
                    "quotation_number": q_num,
                    "vendor_name": vendor,
                    "vendor_tax_id": draft.vendor_tax_id or "",
                    "issue_date": str(issue_date),
                    "expiration_date": str(expiration_date),
                    "currency": draft.currency or "THB",
                    "total_amount": round(total_amount, 2),
                    "items": items,
                })

            except Exception as e:
                drafts.append({
                    "staging_id": f"stage_{unique_prefix}",
                    "temp_file_path": "",
                    "filename": f"gdrive_{item_id[:8]}.pdf",
                    "quotation_number": f"GD-{item_id[:8]}",
                    "vendor_name": "Google Drive Review",
                    "vendor_tax_id": "",
                    "issue_date": str(today),
                    "expiration_date": str(date(today.year, 12, 31)),
                    "currency": "THB",
                    "total_amount": 0.0,
                    "items": [
                        {
                            "item_number": 1,
                            "part_number": "",
                            "description": f"Google Drive File ({item_id})",
                            "quantity": 1.0,
                            "unit": "Pcs",
                            "unit_price": 0.0,
                            "total_price": 0.0,
                        }
                    ],
                    "warning": str(e),
                })

        return {
            "total_files": len(drafts),
            "successful": sum(1 for d in drafts if not d.get("warning")),
            "failed": sum(1 for d in drafts if d.get("warning")),
            "drafts": drafts,
        }

    @app.post("/api/quotations/batch-commit")
    async def batch_commit_endpoint(payload: BatchCommitRequest):
        if payload.user_role != "PH_USER":
            raise HTTPException(status_code=403, detail="Only PH Users can commit quotations")

        os.makedirs("storage/pdf", exist_ok=True)
        results = []
        today = date.today()

        for q in payload.quotations:
            try:
                dest_pdf_path = os.path.join("storage", "pdf", q.filename)
                file_sha256 = ""

                # Move/copy from temp staging if exists
                if q.temp_file_path and os.path.exists(q.temp_file_path):
                    with open(q.temp_file_path, "rb") as f:
                        file_sha256 = hashlib.sha256(f.read()).hexdigest()
                    shutil.copy2(q.temp_file_path, dest_pdf_path)
                elif os.path.exists(dest_pdf_path):
                    with open(dest_pdf_path, "rb") as f:
                        file_sha256 = hashlib.sha256(f.read()).hexdigest()
                else:
                    sample_path = os.path.join("quoatation", q.filename)
                    if os.path.exists(sample_path):
                        dest_pdf_path = sample_path
                        with open(sample_path, "rb") as f:
                            file_sha256 = hashlib.sha256(f.read()).hexdigest()
                    else:
                        file_sha256 = hashlib.sha256(q.filename.encode()).hexdigest()

                # Parse dates
                try:
                    parsed_issue = date.fromisoformat(q.issue_date.strip())
                except Exception:
                    parsed_issue = today

                try:
                    parsed_expiration = date.fromisoformat(q.expiration_date.strip())
                except Exception:
                    parsed_expiration = date(today.year, 12, 31)

                # Format items
                final_items = []
                for idx, it in enumerate(q.items):
                    desc = it.description.strip() if it.description else f"Item {idx + 1}"
                    qty = float(it.quantity) if it.quantity is not None and it.quantity > 0 else 1.0
                    unit = it.unit.strip() if it.unit else "Pcs"
                    price = float(it.unit_price) if it.unit_price is not None and it.unit_price >= 0 else 0.0
                    part_no = it.part_number.strip() if it.part_number and it.part_number.strip() else None

                    final_items.append({
                        "item_number": it.item_number or (idx + 1),
                        "part_number": part_no,
                        "description": desc,
                        "quantity": qty,
                        "unit": unit,
                        "unit_price": price,
                    })

                if not final_items:
                    final_items.append({
                        "item_number": 1,
                        "part_number": None,
                        "description": f"{os.path.splitext(q.filename)[0]} - General Item",
                        "quantity": 1.0,
                        "unit": "Lot",
                        "unit_price": 0.0,
                    })

                registered = service.register_quotation(
                    quotation_number=q.quotation_number.strip(),
                    vendor_name=q.vendor_name.strip(),
                    issue_date=parsed_issue,
                    expiration_date=parsed_expiration,
                    items=final_items,
                    pdf_path=dest_pdf_path,
                    pdf_sha256=file_sha256,
                    user_role=payload.user_role,
                    currency=q.currency.strip() if q.currency else "THB",
                    vendor_tax_id=q.vendor_tax_id.strip() if q.vendor_tax_id else "",
                )

                results.append({
                    "filename": q.filename,
                    "quotation_id": str(registered.quotation_id),
                    "quotation_number": registered.quotation_number,
                    "vendor_name": registered.vendor_name,
                    "items_count": len(final_items),
                    "status": "SUCCESS",
                })
            except Exception as e:
                results.append({
                    "filename": q.filename,
                    "quotation_number": q.quotation_number,
                    "vendor_name": q.vendor_name,
                    "items_count": len(q.items),
                    "status": "ERROR",
                    "error": str(e),
                })

        return {
            "total_quotations": len(payload.quotations),
            "successful": sum(1 for r in results if r["status"] == "SUCCESS"),
            "failed": sum(1 for r in results if r["status"] == "ERROR"),
            "results": results,
        }

    return app
