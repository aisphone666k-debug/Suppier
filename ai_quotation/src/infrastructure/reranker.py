import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from src.domain.quotation import QuotationId, Quotation


@dataclass(frozen=True)
class RerankedCandidate:
    quotation_id: QuotationId
    final_score: float
    vector_score: float
    bm25_score: float
    rrf_score: float
    cross_encoder_score: float
    retrieval_stage: str  # 'VECTOR', 'BM25', 'HYBRID_FUSION'
    matched_highlights: List[str] = field(default_factory=list)


from src.domain.multilingual_lexicon import MultilingualLexicon


class HybridReranker:
    """Multi-stage retrieval reranker combining Reciprocal Rank Fusion (RRF) and Cross-Encoder scoring."""

    def __init__(self, rrf_k: int = 60, weight_vector: float = 0.5, weight_bm25: float = 0.5) -> None:
        self.rrf_k = rrf_k
        self.weight_vector = weight_vector
        self.weight_bm25 = weight_bm25
        self.lexicon = MultilingualLexicon()

    def fuse_and_rerank(
        self,
        query: str,
        vector_results: List[Any],
        bm25_results: List[Any],
        quotations_map: Dict[QuotationId, Quotation],
        top_k: int = 25,
    ) -> List[RerankedCandidate]:
        """Merges Dense Vector matches and BM25 matches using RRF and Cross-Encoder scoring."""
        q_norm = query.strip().lower()
        query_words = [w for w in re.split(r"[\s\-_/.,]+", q_norm) if len(w) >= 2]

        all_qids: Set[QuotationId] = set()
        vector_rank_map: Dict[QuotationId, int] = {}
        vector_score_map: Dict[QuotationId, float] = {}

        for rank, vr in enumerate(vector_results, 1):
            vector_rank_map[vr.quotation_id] = rank
            vector_score_map[vr.quotation_id] = vr.score
            all_qids.add(vr.quotation_id)

        bm25_rank_map: Dict[QuotationId, int] = {}
        bm25_score_map: Dict[QuotationId, float] = {}
        bm25_highlights_map: Dict[QuotationId, List[str]] = {}

        for rank, br in enumerate(bm25_results, 1):
            bm25_rank_map[br.quotation_id] = rank
            bm25_score_map[br.quotation_id] = br.score
            bm25_highlights_map[br.quotation_id] = getattr(br, "matched_fields", [])
            all_qids.add(br.quotation_id)

        candidates: List[RerankedCandidate] = []

        for qid in all_qids:
            v_rank = vector_rank_map.get(qid)
            b_rank = bm25_rank_map.get(qid)

            v_score = vector_score_map.get(qid, 0.0)
            b_score = bm25_score_map.get(qid, 0.0)

            # 1. Reciprocal Rank Fusion (RRF)
            rrf_score = 0.0
            if v_rank is not None:
                rrf_score += self.weight_vector / (self.rrf_k + v_rank)
            if b_rank is not None:
                rrf_score += self.weight_bm25 / (self.rrf_k + b_rank)

            # Determine retrieval stage origin
            if v_rank is not None and b_rank is not None:
                stage = "HYBRID_FUSION"
            elif b_rank is not None:
                stage = "BM25"
            else:
                stage = "VECTOR"

            # 2. Cross-Encoder interaction scoring against actual Quotation text
            quotation = quotations_map.get(qid)
            cross_score = 0.0
            highlights: List[str] = list(bm25_highlights_map.get(qid, []))

            if quotation:
                cross_score = self._compute_cross_encoder_score(
                    q_norm, query_words, quotation, highlights
                )

            # 3. Final Multi-stage Hybrid Score
            if cross_score <= 0.0 and not highlights:
                # Document has neither cross-encoder match nor lexical highlight
                final_score = min(0.35, max(v_score, b_score) * 0.40)
            else:
                normalized_rrf = min(1.0, rrf_score / 0.0163) if rrf_score > 0 else 0.0
                base_max = max(v_score, b_score)
                blend = (
                    0.20 * normalized_rrf
                    + 0.40 * base_max
                    + 0.40 * cross_score
                )
                if cross_score >= 0.35 or "exact_spec_match" in highlights or "exact_part_number" in highlights:
                    final_score = max(base_max, blend)
                else:
                    final_score = blend
                final_score = min(0.99, max(0.0, final_score))

            if final_score > 0.0:
                candidates.append(
                    RerankedCandidate(
                        quotation_id=qid,
                        final_score=round(final_score, 4),
                        vector_score=round(v_score, 4),
                        bm25_score=round(b_score, 4),
                        rrf_score=round(rrf_score, 6),
                        cross_encoder_score=round(cross_score, 4),
                        retrieval_stage=stage,
                        matched_highlights=sorted(list(set(highlights))),
                    )
                )

        # Sort by final score descending
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        return candidates[:top_k]

    def _compute_cross_encoder_score(
        self,
        q_norm: str,
        query_words: List[str],
        quotation: Quotation,
        highlights: List[str],
    ) -> float:
        """Cross-attention scoring between query and quotation contents."""
        norm_q = self.lexicon.normalize_units(q_norm)
        norm_query_words = [w for w in re.split(r"[\s\-_/.,]+", norm_q) if len(w) >= 1]
        if not norm_query_words:
            norm_query_words = query_words

        score = 0.0

        # Check vendor match
        v_name = quotation.vendor_name.lower()
        if q_norm in v_name or any(w in v_name for w in norm_query_words if len(w) >= 3):
            score += 0.35
            highlights.append(f"Vendor: {quotation.vendor_name}")

        # Check quotation number
        q_num = quotation.quotation_number.lower()
        if q_norm in q_num or any(w in q_num for w in norm_query_words if len(w) >= 3):
            score += 0.40
            highlights.append(f"Quote No: {quotation.quotation_number}")

        # Expand synonyms via multilingual lexicon
        expanded_synonyms: Set[str] = set()
        for w in [q_norm, norm_q] + norm_query_words:
            expanded_synonyms.update(self.lexicon.expand_terms(w))
        expanded_synonyms.discard(q_norm)
        expanded_synonyms.discard(norm_q)

        # Extract specification tokens (containing digits or alphanumeric dimensions)
        spec_tokens = re.findall(r"\d+[a-z]+|\d+", norm_q.lower())

        q_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", q_norm)
        best_item_score = 0.0

        for it in quotation.items:
            it_desc = it.description.lower()
            it_pn = (it.part_number or "").lower()
            pn_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", it_pn)
            desc_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", it_desc)
            full_item_text = f"{it_desc} {it_pn}"
            full_compact = f"{desc_compact}{pn_compact}"

            item_score = 0.0
            item_hl = []

            # 1. Exact and Partial Part Number Match
            if it_pn and (q_norm == it_pn or norm_q == it_pn):
                item_score += 0.45
                item_hl.append(f"Exact Part: {it.part_number}")
            elif pn_compact and q_compact and q_compact == pn_compact:
                item_score += 0.45
                item_hl.append(f"Exact Part: {it.part_number}")
            elif it_pn and (q_norm in it_pn or it_pn in q_norm or norm_q in it_pn):
                item_score += 0.38
                item_hl.append(f"Part Match: {it.part_number}")
            elif pn_compact and q_compact and len(q_compact) >= 3 and (q_compact in pn_compact or pn_compact in q_compact):
                item_score += 0.38
                item_hl.append(f"Part Match: {it.part_number}")

            # 2. Description Match
            if q_norm in it_desc or norm_q in it_desc:
                item_score += 0.35
                item_hl.append(f"Item: {it.description}")
            elif desc_compact and q_compact and len(q_compact) >= 4 and (q_compact in desc_compact or desc_compact in q_compact):
                item_score += 0.35
                item_hl.append(f"Item: {it.description}")

            # 3. Multilingual Category / Synonym Match
            syn_matched = False
            for syn in expanded_synonyms:
                if len(syn) >= 3 and (syn in it_desc or (it_pn and syn in it_pn)):
                    if not syn_matched:
                        item_score += 0.35
                        item_hl.append(f"Synonym Match: {syn}")
                        syn_matched = True

            # 4. Specification Match / Mismatch Calibration
            if spec_tokens:
                item_specs = re.findall(r"\d+[a-z]+|\d+", full_item_text)
                matched_specs = [st for st in spec_tokens if st in item_specs]
                if len(matched_specs) == len(spec_tokens) and len(matched_specs) > 0:
                    item_score += 0.45
                    for st in matched_specs:
                        item_hl.append(f"Spec Match: {st}")
                elif len(matched_specs) > 0:
                    item_score += 0.25
                    for st in matched_specs:
                        item_hl.append(f"Spec Match: {st}")
                else:
                    # Query specifically demanded specifications, but this item has none of them
                    item_score *= 0.40

            # 5. Query Term Coverage
            matched_words = 0
            for qw in norm_query_words:
                if qw in full_item_text or qw in full_compact:
                    matched_words += 1
                elif any(syn in full_item_text for syn in self.lexicon.expand_terms(qw) if len(syn) >= 3):
                    matched_words += 1
            if norm_query_words:
                coverage = matched_words / len(norm_query_words)
                item_score *= (0.50 + 0.50 * coverage)

            if item_score > best_item_score:
                best_item_score = item_score
                highlights.extend(item_hl)

        score += best_item_score
        return min(0.99, score)

