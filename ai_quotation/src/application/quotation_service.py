from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional, List
import uuid

from src.domain.quotation import (
    Quotation,
    QuotationId,
    QuotationStatus,
    QuotationItem,
    QuotationAcknowledgment,
)
from src.domain.validity_period import ValidityPeriod
from src.domain.confidence_score import ConfidenceScore
from src.domain.manual_quotation_request import (
    ManualQuotationRequest,
    RequestStatus,
    RequestUrgency,
)
from src.infrastructure.sqlite_quotation_repository import SqliteQuotationRepository
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.infrastructure.search_cache import MemorySearchCache, CacheEntry
from src.infrastructure.vector_index import MemoryVectorIndex
from src.infrastructure.embedding_engine import FastEmbedEngine
from src.infrastructure.bm25_index import BM25Index
from src.infrastructure.reranker import HybridReranker
from src.domain.extracted_quotation_draft import ExtractedQuotationDraft


@dataclass(frozen=True)
class SearchResultView:
    quotation: Quotation
    confidence: ConfidenceScore
    can_receive: bool
    matched_highlights: List[str] = field(default_factory=list)
    retrieval_stage: str = "HYBRID"


class QuotationApplicationService:
    """Orchestrates multi-stage hybrid search discovery (BM25 + Vector + Cross-Encoder Reranking),

    quotation registration, lifecycle renewals, and manual demands.
    """

    def __init__(
        self,
        quotation_repository: SqliteQuotationRepository,
        manual_request_repository: SqliteManualRequestRepository,
        search_cache: MemorySearchCache,
        vector_index: MemoryVectorIndex,
        embedding_engine: FastEmbedEngine,
        bm25_index: Optional[BM25Index] = None,
        reranker: Optional[HybridReranker] = None,
    ) -> None:
        self.quotation_repository = quotation_repository
        self.manual_request_repository = manual_request_repository
        self.search_cache = search_cache
        self.vector_index = vector_index
        self.embedding_engine = embedding_engine
        self.bm25_index = bm25_index or BM25Index()
        self.reranker = reranker or HybridReranker()

    def search(
        self,
        query: str,
        user_role: str,
        reference_date: date,
        min_confidence: float = 0.50,
        bypass_cache: bool = False,
    ) -> list[SearchResultView]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        # 1. Check Key-Value Cache (if not bypassed)
        cached_entries = None if bypass_cache else self.search_cache.get(normalized_query)
        scored_pairs: list[tuple[QuotationId, float, list[str], str]] = []

        if cached_entries is not None and len(cached_entries) > 0:
            scored_pairs = [(e.quotation_id, e.confidence, [], "CACHE") for e in cached_entries]
        else:
            # 2. Multi-Stage Hybrid Retrieval Pipeline:
            # Stage A: Dense Semantic Vector Search (Document & Line-Item Granular Chunks)
            query_vector = self.embedding_engine.embed_text(normalized_query)
            vector_matches = self.vector_index.search(query_vector, limit=35)

            # Stage B: BM25 Lexical Keyword Search (Field Weighted: Part, Description, Vendor, Quote No)
            bm25_matches = self.bm25_index.search(normalized_query, limit=35)

            # Stage C: Fetch candidate quotations for cross-encoder reranking
            candidate_ids = set([vm.quotation_id for vm in vector_matches] + [bm.quotation_id for bm in bm25_matches])
            quotations_map = {}
            for cid in candidate_ids:
                q_entity = self.quotation_repository.find_by_id(cid)
                if q_entity:
                    quotations_map[cid] = q_entity

            # Stage D: Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking
            reranked = self.reranker.fuse_and_rerank(
                query=normalized_query,
                vector_results=vector_matches,
                bm25_results=bm25_matches,
                quotations_map=quotations_map,
                top_k=25,
            )

            scored_pairs = [
                (r.quotation_id, r.final_score, r.matched_highlights, r.retrieval_stage)
                for r in reranked
            ]

            # Write high-quality results to Key-Value Cache
            if scored_pairs:
                cache_entries = [
                    CacheEntry(quotation_id=qid, confidence=score)
                    for qid, score, _, _ in scored_pairs
                ]
                self.search_cache.put(normalized_query, cache_entries)

        # 3. Fetch Quotation Entities and Apply Business Rules
        results: list[SearchResultView] = []
        top_score = scored_pairs[0][1] if scored_pairs else 0.0
        has_highlights_anywhere = any(bool(h) for _, _, h, _ in scored_pairs)
        cutoff = 0.60 if (top_score >= 0.70 and has_highlights_anywhere) else min_confidence

        for qid, score, highlights, stage in scored_pairs:
            # Filter low-scoring noise when strong matches exist
            if score < cutoff and not highlights:
                continue


            quotation = self.quotation_repository.find_by_id(qid)
            if not quotation:
                continue

            quotation.evaluate_expiration(reference_date)

            # Normal Users ONLY see ACTIVE quotations
            if user_role == "NORMAL_USER" and quotation.status != QuotationStatus.ACTIVE:
                continue

            confidence = ConfidenceScore(round(score, 4))
            can_receive = quotation.can_be_received(reference_date)

            results.append(
                SearchResultView(
                    quotation=quotation,
                    confidence=confidence,
                    can_receive=can_receive,
                    matched_highlights=highlights,
                    retrieval_stage=stage,
                )
            )

        return results

    def register_quotation(
        self,
        quotation_number: str,
        vendor_name: str,
        issue_date: date,
        expiration_date: date,
        items: list[dict[str, Any]],
        pdf_path: str,
        pdf_sha256: str,
        user_role: str,
        currency: str = "THB",
        vendor_tax_id: Optional[str] = None,
        raw_text: Optional[str] = None,
    ) -> Quotation:
        if user_role != "PH_USER":
            raise PermissionError("Only PH Users are authorized to register quotations")

        qid = QuotationId(f"QT-{quotation_number.strip()}")
        validity = ValidityPeriod(issue_date=issue_date, expiration_date=expiration_date)

        quotation_items = tuple(
            QuotationItem(
                item_number=i["item_number"],
                description=i["description"],
                quantity=float(i["quantity"]),
                unit=i["unit"],
                unit_price=float(i["unit_price"]),
                part_number=i.get("part_number"),
                drawing_number=i.get("drawing_number"),
            )
            for i in items
        )

        quotation = Quotation(
            quotation_id=qid,
            quotation_number=quotation_number,
            vendor_name=vendor_name,
            validity_period=validity,
            status=QuotationStatus.ACTIVE,
            items=quotation_items,
            pdf_path=pdf_path,
            pdf_sha256=pdf_sha256,
            currency=currency,
            vendor_tax_id=vendor_tax_id,
            raw_text=raw_text,
        )

        # 1. Save to relational storage
        self.quotation_repository.save(quotation)

        # 2. Index into both BM25 and Vector indices
        self.index_quotation(quotation)

        # 3. Invalidate search cache
        self.search_cache.invalidate_all()

        return quotation

    def index_quotation(self, quotation: Quotation) -> None:
        """Indexes an existing quotation entity into BM25 lexical and Vector semantic indices."""
        part_numbers = [it.part_number for it in quotation.items if it.part_number]
        drawing_numbers = [getattr(it, "drawing_number", None) for it in quotation.items if getattr(it, "drawing_number", None)]
        all_part_dwg = list(dict.fromkeys(part_numbers + drawing_numbers))
        descriptions = [it.description for it in quotation.items if it.description]

        # 1. Index into BM25 engine
        self.bm25_index.add_document(
            quotation_id=quotation.quotation_id,
            quotation_number=quotation.quotation_number,
            vendor_name=quotation.vendor_name,
            part_numbers=all_part_dwg,
            descriptions=descriptions,
            raw_text=quotation.raw_text or "",
        )

        # 2. Index composite quotation into Vector index
        keywords = [quotation.vendor_name, quotation.quotation_number] + descriptions + all_part_dwg
        if quotation.raw_text:
            keywords.append(quotation.raw_text)

        composite_text = f"Quotation {quotation.quotation_number} from {quotation.vendor_name}. Items: {' | '.join(descriptions)}. Drawing/Parts: {' '.join(all_part_dwg)}. {quotation.raw_text or ''}"
        vector = self.embedding_engine.embed_text(composite_text)
        self.vector_index.add(quotation.quotation_id, vector, keywords=keywords)

        # 3. Index granular line items for precision item-level vector matching
        for it in quotation.items:
            item_text = f"{it.description} {it.part_number or ''} {quotation.vendor_name}"
            it_vec = self.embedding_engine.embed_text(item_text)
            self.vector_index.add_chunk(
                chunk_id=f"{quotation.quotation_id}_it_{it.item_number}",
                quotation_id=quotation.quotation_id,
                vector=it_vec,
                label=f"Item #{it.item_number}: {it.description}",
            )

    def reindex_all(self) -> int:
        """Re-indexes all quotations from repository into BM25 and Vector indices."""
        all_quotations = self.quotation_repository.find_all()
        for q in all_quotations:
            self.index_quotation(q)
        return len(all_quotations)

    def renew_quotation(
        self,
        quotation_id: QuotationId,
        new_expiration_date: date,
        user_role: str,
        reference_date: date,
        remarks: str = "",
    ) -> Quotation:
        if user_role != "PH_USER":
            raise PermissionError("Only PH Users are authorized to renew quotations")

        quotation = self.quotation_repository.find_by_id(quotation_id)
        if not quotation:
            raise KeyError(f"Quotation {quotation_id} not found")

        quotation.renew(
            new_expiration_date=new_expiration_date,
            reference_date=reference_date,
            remarks=remarks,
        )

        self.quotation_repository.save(quotation)
        self.search_cache.invalidate_all()
        return quotation

    def acknowledge_quotation(
        self,
        quotation_id: QuotationId,
        user_id: str,
        reference_date: date,
    ) -> QuotationAcknowledgment:
        quotation = self.quotation_repository.find_by_id(quotation_id)
        if not quotation:
            raise KeyError(f"Quotation {quotation_id} not found")

        ack = quotation.receive(user_id=user_id, reference_date=reference_date)
        self.quotation_repository.record_acknowledgment(ack)
        return ack

    def submit_manual_request(
        self,
        requester_user_id: str,
        department: str,
        item_description: str,
        part_number: Optional[str] = None,
        target_quantity: Optional[float] = None,
        target_unit: Optional[str] = None,
        needed_by_date: Optional[date] = None,
        urgency: RequestUrgency = RequestUrgency.NORMAL,
    ) -> ManualQuotationRequest:
        ticket_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        request = ManualQuotationRequest(
            ticket_id=ticket_id,
            requester_user_id=requester_user_id,
            department=department,
            item_description=item_description,
            part_number=part_number,
            target_quantity=target_quantity,
            target_unit=target_unit,
            needed_by_date=needed_by_date,
            urgency=urgency,
        )
        self.manual_request_repository.save(request)
        return request

    def list_pending_manual_requests(self) -> list[ManualQuotationRequest]:
        return self.manual_request_repository.find_by_status(RequestStatus.SUBMITTED)

    def fulfill_manual_request(
        self,
        ticket_id: str,
        quotation_id: QuotationId,
        ph_user_id: str,
        user_role: str,
    ) -> ManualQuotationRequest:
        if user_role != "PH_USER":
            raise PermissionError("Only PH Users can fulfill manual requests")

        req = self.manual_request_repository.find_by_ticket_id(ticket_id)
        if not req:
            raise KeyError(f"Manual request {ticket_id} not found")

        quotation = self.quotation_repository.find_by_id(quotation_id)
        if not quotation:
            raise KeyError(f"Quotation {quotation_id} not found")

        req.fulfill(quotation_id=quotation_id, ph_user_id=ph_user_id)
        self.manual_request_repository.save(req)
        return req

    def list_expired_quotations(self, reference_date: date) -> list[Quotation]:
        return self.quotation_repository.find_expired(reference_date=reference_date)

    def list_all_quotations(self) -> list[Quotation]:
        return self.quotation_repository.find_all()

    def extract_draft_from_pdf(self, pdf_path: str, user_role: str) -> ExtractedQuotationDraft:
        """Auto-extracts quotation draft from a PDF document for PH users using intelligent extraction."""
        if user_role != "PH_USER":
            raise PermissionError("Only PH Users are authorized to auto-extract quotation drafts")

        from src.infrastructure.pdf_reader import PdfDocumentReader
        reader = PdfDocumentReader()
        return reader.extract_draft(pdf_path)
