from dataclasses import dataclass
from datetime import date
from typing import Any, Optional
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
from src.domain.extracted_quotation_draft import ExtractedQuotationDraft


@dataclass(frozen=True)
class SearchResultView:
    quotation: Quotation
    confidence: ConfidenceScore
    can_receive: bool


class QuotationApplicationService:
    """Orchestrates search discovery, quotation registration, renewals, and manual demands."""

    def __init__(
        self,
        quotation_repository: SqliteQuotationRepository,
        manual_request_repository: SqliteManualRequestRepository,
        search_cache: MemorySearchCache,
        vector_index: MemoryVectorIndex,
        embedding_engine: FastEmbedEngine,
    ) -> None:
        self.quotation_repository = quotation_repository
        self.manual_request_repository = manual_request_repository
        self.search_cache = search_cache
        self.vector_index = vector_index
        self.embedding_engine = embedding_engine

    def search(
        self,
        query: str,
        user_role: str,
        reference_date: date,
        min_confidence: float = 0.65,
    ) -> list[SearchResultView]:


        normalized_query = query.strip()
        if not normalized_query:
            return []

        # 1. Check Key-Value Cache
        cached_entries = self.search_cache.get(normalized_query)
        scored_pairs: list[tuple[QuotationId, float]] = []

        if cached_entries is not None:
            scored_pairs = [(e.quotation_id, e.confidence) for e in cached_entries]
        else:
            # 2. Hybrid Retrieval: Exact Tokens + Semantic Embeddings
            query_vector = self.embedding_engine.embed_text(normalized_query)
            vector_matches = self.vector_index.search(query_vector, limit=25)

            # Token matches (e.g. exact part numbers, codes, Thai, Japanese words)
            from src.domain.multilingual_lexicon import MultilingualLexicon
            lexicon = MultilingualLexicon()
            query_tokens = lexicon.extract_unicode_tokens(normalized_query)
            if not query_tokens:
                query_tokens = [normalized_query.lower()]
            token_matches = self.vector_index.search_by_tokens(query_tokens)


            # Merge and pick highest score per quotation
            score_map: dict[QuotationId, float] = {}
            for vm in vector_matches:
                score_map[vm.quotation_id] = max(score_map.get(vm.quotation_id, 0.0), vm.score)
            for tm in token_matches:
                score_map[tm.quotation_id] = max(score_map.get(tm.quotation_id, 0.0), tm.score)

            scored_pairs = sorted(score_map.items(), key=lambda x: x[1], reverse=True)

            # Write to Key-Value Cache
            cache_entries = [CacheEntry(quotation_id=qid, confidence=score) for qid, score in scored_pairs]
            self.search_cache.put(normalized_query, cache_entries)

        # 3. Fetch Quotation Entities and Apply Business Rules
        results: list[SearchResultView] = []
        for qid, score in scored_pairs:
            if score < min_confidence:
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

        # 2. Index into vector index
        self.index_quotation(quotation)

        # 3. Invalidate search cache
        self.search_cache.invalidate_all()

        return quotation

    def index_quotation(self, quotation: Quotation) -> None:
        """Indexes an existing quotation entity into vector index with semantic embedding and keywords."""
        keywords = [quotation.vendor_name, quotation.quotation_number]
        item_texts = []
        for it in quotation.items:
            keywords.append(it.description)
            if it.part_number:
                keywords.append(it.part_number)
            item_texts.append(f"{it.description} {it.part_number or ''}")

        if quotation.raw_text:
            keywords.append(quotation.raw_text)

        composite_text = f"Quotation {quotation.quotation_number} from {quotation.vendor_name}. Items: {' | '.join(item_texts)}. {quotation.raw_text or ''}"
        vector = self.embedding_engine.embed_text(composite_text)
        self.vector_index.add(quotation.quotation_id, vector, keywords=keywords)

    def reindex_all(self) -> int:
        """Re-indexes all quotations from repository into vector index."""
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
        """Auto-extracts quotation draft from a PDF document for PH users to eliminate manual input."""
        if user_role != "PH_USER":
            raise PermissionError("Only PH Users are authorized to auto-extract quotation drafts")

        from src.infrastructure.pdf_reader import PdfDocumentReader
        reader = PdfDocumentReader()
        return reader.extract_draft(pdf_path)
