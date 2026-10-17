from dataclasses import dataclass
from datetime import date
import logging
import time
from typing import Optional

from src.application.inquiry_generator import AnswerGeneratorPort, QuotationChunkContext, QuotationCitationView
from src.application.quotation_service import QuotationApplicationService
from src.infrastructure.inquiry_cache import MemoryInquiryCache

logger = logging.getLogger("quotation_finder.rag")


@dataclass(frozen=True)
class InquiryResultView:
    answer: str
    cached: bool
    retrieval_duration_ms: float
    generation_duration_ms: float
    total_duration_ms: float
    retrieved_quotations_count: int
    citations: tuple[QuotationCitationView, ...] = ()


class QuotationInquiryService:
    """Application use case for natural language inquiry and RAG question-answering over quotations."""

    def __init__(
        self,
        quotation_service: QuotationApplicationService,
        answer_generator: AnswerGeneratorPort,
        inquiry_cache: Optional[MemoryInquiryCache] = None,
        top_k: int = 4,
    ) -> None:
        self.quotation_service = quotation_service
        self.answer_generator = answer_generator
        self.inquiry_cache = inquiry_cache or MemoryInquiryCache()
        self.top_k = top_k

    @staticmethod
    def _is_catalog_overview_intent(query: str) -> bool:
        lower_q = query.lower().strip()
        thai_overview_keywords = [
            "มีอะไรบ้าง",
            "มีอะบ้าง",
            "มีอะไร",
            "มีสินค้าอะไร",
            "มีรายการอะไร",
            "ขอรายการทั้งหมด",
            "รายการทั้งหมด",
            "ดูทั้งหมด",
            "มีใบเสนอราคาอะไร",
            "มีของอะไร",
        ]
        if any(kw in lower_q for kw in thai_overview_keywords):
            return True
        english_overview_keywords = [
            "what do you have",
            "what items",
            "overview",
            "catalog",
            "list all",
            "show all",
            "all quotations",
            "available quotations",
        ]
        return any(kw in lower_q for kw in english_overview_keywords)

    def _map_quotation_to_chunk(self, q) -> QuotationChunkContext:
        items_desc = "; ".join(
            f"{item.description} (Part: {item.part_number or 'N/A'}, Qty: {item.quantity} {item.unit}, Unit Price: {item.unit_price} {q.currency})"
            for item in q.items
        )
        val_desc = f"Valid from {q.validity_period.issue_date} to {q.validity_period.expiration_date} ({q.status.value})"
        raw_snippet = q.raw_text[:1200] if getattr(q, "raw_text", None) else None
        return QuotationChunkContext(
            quotation_number=q.quotation_number,
            vendor_name=q.vendor_name,
            currency=q.currency,
            items_summary=items_desc,
            validity_summary=val_desc,
            quotation_id=str(q.quotation_id),
            vendor_tax_id=q.vendor_tax_id,
            raw_text_snippet=raw_snippet,
        )

    def _map_quotations_to_citations(self, quotations: list) -> tuple[QuotationCitationView, ...]:
        citations = []
        for q in quotations:
            first_item = q.items[0] if q.items else None
            item_desc = first_item.description if first_item else "Quotation Item"
            part_no = f" ({first_item.part_number})" if first_item and first_item.part_number else ""
            summary = f"{item_desc}{part_no}"
            price = f"{first_item.unit_price} {q.currency}" if first_item else f"0 {q.currency}"
            search_query = first_item.description if first_item else q.quotation_number
            citations.append(
                QuotationCitationView(
                    quotation_id=str(q.quotation_id),
                    quotation_number=q.quotation_number,
                    vendor_name=q.vendor_name,
                    items_summary=summary,
                    price_summary=price,
                    status=q.status.value,
                    search_query=search_query,
                )
            )
        return tuple(citations)

    def answer_inquiry_with_telemetry(
        self,
        query: str,
        user_role: str = "NORMAL_USER",
        reference_date: Optional[date] = None,
    ) -> InquiryResultView:
        """Retrieves matching quotations, generates a grounded answer, and records telemetry and caching metrics."""
        start_total = time.perf_counter()

        if not query or not query.strip():
            return InquiryResultView(
                answer="Please provide a specific quotation question or part description.",
                cached=False,
                retrieval_duration_ms=0.0,
                generation_duration_ms=0.0,
                total_duration_ms=0.0,
                retrieved_quotations_count=0,
                citations=(),
            )

        clean_query = query.strip()
        ref_date = reference_date or date.today()

        # Step 0: Check Inquiry Cache for high-speed response
        cached_entry = self.inquiry_cache.get_entry(clean_query, user_role=user_role)
        if cached_entry is not None:
            cached_answer, cached_citations = cached_entry
            total_duration_ms = round((time.perf_counter() - start_total) * 1000.0, 2)
            logger.info(
                "[RAG_CACHE_HIT] query='%s' role='%s' total_ms=%.2f",
                clean_query,
                user_role,
                total_duration_ms,
            )
            return InquiryResultView(
                answer=cached_answer,
                cached=True,
                retrieval_duration_ms=0.0,
                generation_duration_ms=0.0,
                total_duration_ms=total_duration_ms,
                retrieved_quotations_count=len(cached_citations),
                citations=cached_citations,
            )

        # Step 1: Retrieval stage (multilingual semantic search or catalog overview)
        start_retrieval = time.perf_counter()
        source_quotations = []
        if self._is_catalog_overview_intent(clean_query):
            all_quotations = self.quotation_service.quotation_repository.find_all()
            matching_quotations = [
                q for q in all_quotations
                if (hasattr(q, "can_be_received") and q.can_be_received(ref_date))
                or getattr(q, "status", None) == "ACTIVE"
                or user_role == "PH_USER"
            ]
            candidates = matching_quotations if matching_quotations else all_quotations
            source_quotations = candidates[: self.top_k * 2]
            chunks = [self._map_quotation_to_chunk(q) for q in source_quotations]
            retrieval_duration_ms = round((time.perf_counter() - start_retrieval) * 1000.0, 2)

            if not chunks:
                total_duration_ms = round((time.perf_counter() - start_total) * 1000.0, 2)
                return InquiryResultView(
                    answer="There are no quotations registered in the system yet.",
                    cached=False,
                    retrieval_duration_ms=retrieval_duration_ms,
                    generation_duration_ms=0.0,
                    total_duration_ms=total_duration_ms,
                    retrieved_quotations_count=0,
                    citations=(),
                )
        else:
            search_results = self.quotation_service.search(
                query=clean_query,
                user_role=user_role,
                reference_date=ref_date,
            )
            retrieval_duration_ms = round((time.perf_counter() - start_retrieval) * 1000.0, 2)

            if not search_results:
                total_duration_ms = round((time.perf_counter() - start_total) * 1000.0, 2)
                empty_msg = (
                    f"No matching quotation found for '{clean_query}'. "
                    "You can submit a manual quotation request via the 'Request Quotation Manually' button."
                )
                logger.info(
                    "[RAG_MISS_EMPTY] query='%s' role='%s' retrieval_ms=%.2f total_ms=%.2f",
                    clean_query,
                    user_role,
                    retrieval_duration_ms,
                    total_duration_ms,
                )
                return InquiryResultView(
                    answer=empty_msg,
                    cached=False,
                    retrieval_duration_ms=retrieval_duration_ms,
                    generation_duration_ms=0.0,
                    total_duration_ms=total_duration_ms,
                    retrieved_quotations_count=0,
                    citations=(),
                )

            top_results = search_results[: self.top_k]
            source_quotations = [res.quotation for res in top_results]
            chunks = [self._map_quotation_to_chunk(q) for q in source_quotations]

        citations = self._map_quotations_to_citations(source_quotations)

        # Step 3: Generation stage (grounded LLM synthesis)
        start_generation = time.perf_counter()
        answer = self.answer_generator.generate_answer(query=clean_query, context_chunks=chunks)
        generation_duration_ms = round((time.perf_counter() - start_generation) * 1000.0, 2)
        total_duration_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

        # Save to inquiry cache with citations for subsequent queries
        self.inquiry_cache.put(clean_query, user_role=user_role, answer=answer, citations=citations)

        logger.info(
            "[RAG_GENERATED] query='%s' role='%s' chunks=%d retrieval_ms=%.2f gen_ms=%.2f total_ms=%.2f",
            clean_query,
            user_role,
            len(chunks),
            retrieval_duration_ms,
            generation_duration_ms,
            total_duration_ms,
        )

        return InquiryResultView(
            answer=answer,
            cached=False,
            retrieval_duration_ms=retrieval_duration_ms,
            generation_duration_ms=generation_duration_ms,
            total_duration_ms=total_duration_ms,
            retrieved_quotations_count=len(chunks),
            citations=citations,
        )

    def answer_inquiry(
        self,
        query: str,
        user_role: str = "NORMAL_USER",
        reference_date: Optional[date] = None,
    ) -> str:
        """Convenience method returning string answer for backward compatibility."""
        return self.answer_inquiry_with_telemetry(query, user_role, reference_date).answer
