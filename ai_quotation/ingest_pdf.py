import sys
import os
from pathlib import Path
from datetime import date

base_dir = Path(__file__).resolve().parent
cache_dir = base_dir / ".cache"
os.environ.setdefault("HF_HOME", str(cache_dir / "huggingface"))
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(cache_dir / "fastembed"))
temp_dir = cache_dir / "temp"
temp_dir.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(temp_dir)
os.environ["TMP"] = str(temp_dir)

import sqlite3
from src.infrastructure.pdf_reader import PdfDocumentReader
from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.infrastructure.search_cache import MemorySearchCache
from src.infrastructure.vector_index import MemoryVectorIndex
from src.infrastructure.embedding_engine import FastEmbedEngine
from src.application.quotation_service import QuotationApplicationService


def get_service(db_path: str = "quotations.db") -> QuotationApplicationService:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    q_repo = SqliteQuotationRepository(conn)
    q_repo.initialize_schema()
    m_repo = SqliteManualRequestRepository(conn)
    m_repo.initialize_schema()
    cache = MemorySearchCache()
    v_index = MemoryVectorIndex()
    emb = FastEmbedEngine()
    service = QuotationApplicationService(
        quotation_repository=q_repo,
        manual_request_repository=m_repo,
        search_cache=cache,
        vector_index=v_index,
        embedding_engine=emb,
    )
    service.reindex_all()
    return service


def ingest_pdf(pdf_path: str, service: QuotationApplicationService, user_role: str = "PH_USER", verbose: bool = True):
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found: {pdf_path}")
        return None

    reader = PdfDocumentReader()
    draft = reader.extract_draft(pdf_path)

    items_payload = [
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

    registered = service.register_quotation(
        quotation_number=draft.quotation_number,
        vendor_name=draft.vendor_name,
        issue_date=draft.issue_date,
        expiration_date=draft.expiration_date,
        items=items_payload,
        pdf_path=pdf_path,
        pdf_sha256=draft.sha256,
        user_role=user_role,
        currency=draft.currency,
        vendor_tax_id=draft.vendor_tax_id,
        raw_text=draft.raw_text,
    )

    if verbose:
        print(f"[SUCCESS] {os.path.basename(pdf_path)} -> QT#: {draft.quotation_number} | Vendor: {draft.vendor_name} | Items: {len(draft.items)} | Exp: {draft.expiration_date}")
    return registered


def ingest_batch(target_path: str, db_path: str = "quotations.db"):
    if not os.path.exists(target_path):
        print(f"[ERROR] Path does not exist: {target_path}")
        return

    service = get_service(db_path)

    if os.path.isfile(target_path):
        pdf_files = [target_path]
    elif os.path.isdir(target_path):
        pdf_files = [
            os.path.join(target_path, f)
            for f in sorted(os.listdir(target_path))
            if f.lower().endswith(".pdf")
        ]
    else:
        print(f"[ERROR] Invalid path: {target_path}")
        return

    if not pdf_files:
        print(f"[WARN] No PDF files found in {target_path}")
        return

    print("=" * 70)
    print(f" BATCH PDF INGESTION: Found {len(pdf_files)} PDF file(s)")
    print(f" Target Database: {db_path}")
    print("=" * 70)

    success_count = 0
    error_count = 0

    for idx, pdf in enumerate(pdf_files, 1):
        print(f"[{idx}/{len(pdf_files)}] Ingesting {os.path.basename(pdf)}...", end=" ")
        try:
            res = ingest_pdf(pdf, service, verbose=False)
            if res:
                print(f"[OK] QT#: {res.quotation_number} | Vendor: {res.vendor_name} | Items: {len(res.items)}")
                success_count += 1
            else:
                print("[FAILED]")
                error_count += 1
        except Exception as e:
            print(f"[ERROR: {e}]")
            error_count += 1

    print("=" * 70)
    print(f" BATCH COMPLETE: {success_count} succeeded, {error_count} failed.")
    print(" All items are now indexed and instantly searchable!")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single file:  uv run python ingest_pdf.py <path_to_pdf>")
        print("  Batch folder: uv run python ingest_pdf.py <path_to_directory>")
        print("\nExamples:")
        print("  uv run python ingest_pdf.py \"quoatation/QT NO. 137836.pdf\"")
        print("  uv run python ingest_pdf.py quoatation/")
        sys.exit(1)

    target = sys.argv[1]
    ingest_batch(target)
