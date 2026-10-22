import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from src.domain.quotation import QuotationId
from src.domain.multilingual_lexicon import MultilingualLexicon


@dataclass(frozen=True)
class BM25SearchResult:
    quotation_id: QuotationId
    score: float
    matched_terms: List[str] = field(default_factory=list)
    matched_fields: List[str] = field(default_factory=list)


@dataclass
class DocumentFields:
    quotation_id: QuotationId
    quotation_number: str
    vendor_name: str
    part_numbers: List[str]
    descriptions: List[str]
    raw_text: str
    # Pre-computed tokens with weights
    tokens: Dict[str, float] = field(default_factory=dict)
    length: float = 0.0


class BM25Index:
    """Enterprise-grade Okapi BM25 search engine with field weighting and multilingual tokenization.

    Fields weighting:
      - part_numbers: 3.5x
      - quotation_number: 3.0x
      - descriptions: 2.5x
      - vendor_name: 2.0x
      - raw_text: 1.0x
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._lexicon = MultilingualLexicon()
        self._documents: Dict[QuotationId, DocumentFields] = {}
        # Inverted index: token -> dict of (quotation_id -> weighted_term_frequency)
        self._inverted_index: Dict[str, Dict[QuotationId, float]] = {}
        # Document frequencies: token -> count of docs containing token
        self._doc_frequencies: Dict[str, int] = {}
        self._avg_doc_length: float = 0.0

    def __len__(self) -> int:
        return len(self._documents)

    def _tokenize(self, text: str) -> List[str]:
        """Extracts normalized words, alphanumeric terms, and expanded multilingual synonyms."""
        if not text:
            return []
        tokens: List[str] = []
        raw_clean = self._lexicon.normalize_units(text.lower().strip())

        # 1. Alphanumeric parts & codes (e.g. 5V-1400, A-61(S), EW32EAG, H7CC-ASD)
        code_tokens = re.findall(r"[a-z0-9]+(?:[-_/.][a-z0-9]+)*", raw_clean)
        tokens.extend(code_tokens)

        # Also strip hyphens/dots for concatenated matching (e.g., "5v1400" for "5v-1400")
        for ct in code_tokens:
            compact = re.sub(r"[-_/.]", "", ct)
            if compact and compact != ct:
                tokens.append(compact)
            # Add subcomponents of hyphenated parts
            subparts = re.split(r"[-_/.]", ct)
            if len(subparts) > 1:
                tokens.extend([sp for sp in subparts if len(sp) >= 2])

        # Alphanumeric transition splitting (e.g. "belt7m" -> ["belt", "7m"], "7m1360" -> ["7m", "1360"])
        split_tokens = []
        for ct in list(tokens):
            parts = re.split(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", ct)
            if len(parts) > 1:
                split_tokens.extend([p for p in parts if len(p) >= 1])
        tokens.extend(split_tokens)

        # Whole phrase compacted without any spaces or symbols (e.g. "Belt 7M 1360" -> "belt7m1360")
        compact_phrase = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", raw_clean)
        if compact_phrase and len(compact_phrase) >= 3 and compact_phrase not in tokens:
            tokens.append(compact_phrase)

        # 2. Unicode words (Thai, Japanese, general Latin)
        unicode_words = self._lexicon.extract_unicode_tokens(raw_clean)
        for w in unicode_words:
            w_norm = w.strip().lower()
            if w_norm and w_norm not in tokens:
                tokens.append(w_norm)
            # Expand cross-lingual synonyms
            for syn in self._lexicon.expand_terms(w_norm):
                if syn and syn not in tokens:
                    tokens.append(syn)

        return list(dict.fromkeys(tokens))


    def add_document(
        self,
        quotation_id: QuotationId,
        quotation_number: str,
        vendor_name: str,
        part_numbers: List[str],
        descriptions: List[str],
        raw_text: str = "",
    ) -> None:
        """Indexes quotation into BM25 inverted index with weighted fields."""
        # Remove existing if already present
        if quotation_id in self._documents:
            self.remove_document(quotation_id)

        weighted_tf: Dict[str, float] = {}

        def record_field(text: str, weight: float) -> None:
            if not text:
                return
            t_list = self._tokenize(text)
            for t in t_list:
                weighted_tf[t] = weighted_tf.get(t, 0.0) + weight

        # Field weighting
        record_field(quotation_number, 3.0)
        record_field(vendor_name, 2.0)
        for pn in part_numbers:
            if pn:
                record_field(pn, 3.5)
        for desc in descriptions:
            if desc:
                record_field(desc, 2.5)
        if raw_text:
            record_field(raw_text, 1.0)

        doc_length = sum(weighted_tf.values())
        doc_fields = DocumentFields(
            quotation_id=quotation_id,
            quotation_number=quotation_number,
            vendor_name=vendor_name,
            part_numbers=part_numbers,
            descriptions=descriptions,
            raw_text=raw_text,
            tokens=weighted_tf,
            length=doc_length,
        )
        self._documents[quotation_id] = doc_fields

        # Update inverted index and document frequencies
        for token, w_freq in weighted_tf.items():
            if token not in self._inverted_index:
                self._inverted_index[token] = {}
                self._doc_frequencies[token] = 0
            self._inverted_index[token][quotation_id] = w_freq
            self._doc_frequencies[token] += 1

        self._recompute_avg_doc_length()

    def remove_document(self, quotation_id: QuotationId) -> None:
        if quotation_id not in self._documents:
            return
        doc = self._documents.pop(quotation_id)
        for token in doc.tokens.keys():
            if token in self._inverted_index:
                self._inverted_index[token].pop(quotation_id, None)
                self._doc_frequencies[token] -= 1
                if self._doc_frequencies[token] <= 0:
                    del self._doc_frequencies[token]
                    del self._inverted_index[token]
        self._recompute_avg_doc_length()

    def _recompute_avg_doc_length(self) -> None:
        if not self._documents:
            self._avg_doc_length = 0.0
            return
        total_len = sum(d.length for d in self._documents.values())
        self._avg_doc_length = total_len / len(self._documents)

    def _compute_idf(self, token: str) -> float:
        n = self._doc_frequencies.get(token, 0)
        total_docs = len(self._documents)
        if n == 0 or total_docs == 0:
            return 0.0
        # Standard Okapi BM25 Robertson-Sparck Jones IDF with smoothing
        return math.log(1.0 + (total_docs - n + 0.5) / (n + 0.5))

    def search(self, query: str, limit: int = 50) -> List[BM25SearchResult]:
        """Executes BM25 ranking against query with exact part number substring bonuses."""
        if not self._documents or not query.strip():
            return []

        q_clean = query.strip().lower()
        norm_query = self._lexicon.normalize_units(q_clean)
        q_tokens = self._tokenize(norm_query)
        if not q_tokens:
            q_tokens = [q_clean]

        scores: Dict[QuotationId, float] = {}
        matched_terms_map: Dict[QuotationId, Set[str]] = {}
        matched_fields_map: Dict[QuotationId, Set[str]] = {}

        total_docs = len(self._documents)
        avg_dl = max(1.0, self._avg_doc_length)

        # Group distinct query concepts to avoid synonym cluster inflation
        raw_words = [w for w in re.split(r"[\s\-_/.,]+", norm_query) if len(w) >= 1]
        concepts: List[Set[str]] = []
        for rw in raw_words:
            c_set = set(self._lexicon.expand_terms(rw))
            c_set.add(rw)
            parts = re.split(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", rw)
            if len(parts) > 1:
                c_set.update([p for p in parts if len(p) >= 1])
            concepts.append(c_set)

        if not concepts:
            concepts = [{q_clean}]

        # Track score per concept per document
        doc_concept_scores: Dict[QuotationId, List[float]] = {
            qid: [0.0] * len(concepts) for qid in self._documents.keys()
        }

        for c_idx, c_tokens in enumerate(concepts):
            for token in c_tokens:
                if token not in self._inverted_index:
                    continue
                idf = self._compute_idf(token)
                if idf <= 0:
                    idf = 0.1

                doc_postings = self._inverted_index[token]
                for qid, tf in doc_postings.items():
                    doc = self._documents[qid]
                    dl = doc.length
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (dl / avg_dl))
                    bm25_score = idf * (numerator / denominator)

                    prev_best = doc_concept_scores[qid][c_idx]
                    if bm25_score > prev_best:
                        doc_concept_scores[qid][c_idx] = bm25_score + 0.05 * prev_best
                    else:
                        doc_concept_scores[qid][c_idx] += 0.05 * bm25_score

                    if qid not in matched_terms_map:
                        matched_terms_map[qid] = set()
                        matched_fields_map[qid] = set()
                    matched_terms_map[qid].add(token)

        # Aggregate concept scores with coordination factor (Query Term Coverage)
        for qid, c_scores in doc_concept_scores.items():
            base_sum = sum(c_scores)
            if base_sum <= 0:
                continue
            matched_count = sum(1 for s in c_scores if s > 0)
            total_c = len(concepts)
            coverage = matched_count / total_c
            coordination = 0.40 + 0.60 * (coverage ** 1.3)
            scores[qid] = base_sum * coordination

        # Extract specification tokens (containing digits or alphanumeric codes)
        spec_tokens = re.findall(r"\d+[a-z]+|\d+", norm_query.lower())

        # Apply exact, partial, compact stripped, and specification bonuses
        q_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", q_clean)
        for qid, doc in self._documents.items():
            bonus = 0.0
            fields: Set[str] = matched_fields_map.get(qid, set())
            doc_all_text = " ".join(doc.part_numbers + doc.descriptions).lower()
            doc_all_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", doc_all_text)

            # Specification token alignment bonus
            if spec_tokens:
                doc_specs = re.findall(r"\d+[a-z]+|\d+", doc_all_text)
                matched_specs = [st for st in spec_tokens if st in doc_specs]
                if len(matched_specs) == len(spec_tokens) and len(matched_specs) > 0:
                    bonus += 15.0
                    fields.add("exact_spec_match")
                elif len(matched_specs) > 0:
                    bonus += 7.0
                    fields.add("partial_spec_match")

            # 1. Part number matching (Exact, partial, and compact stripped)
            for pn in doc.part_numbers:
                if not pn:
                    continue
                pn_lower = pn.lower()
                pn_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", pn_lower)
                if q_clean == pn_lower or (q_compact and q_compact == pn_compact):
                    bonus += 15.0
                    fields.add("exact_part_number")
                elif q_clean in pn_lower or pn_lower in q_clean:
                    bonus += 8.0
                    fields.add("partial_part_number")
                elif q_compact and pn_compact and len(q_compact) >= 3 and (q_compact in pn_compact or pn_compact in q_compact):
                    bonus += 10.0
                    fields.add("compact_part_match")

            # 2. Quotation number match
            q_num_lower = doc.quotation_number.lower()
            q_num_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", q_num_lower)
            if q_clean in q_num_lower or (q_compact and q_compact in q_num_compact):
                bonus += 8.0
                fields.add("quotation_number")

            # 3. Vendor match
            vendor_lower = doc.vendor_name.lower()
            vendor_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", vendor_lower)
            if q_clean in vendor_lower or (q_compact and q_compact in vendor_compact) or any(t in vendor_lower for t in q_tokens if len(t) >= 3):
                bonus += 6.0
                fields.add("vendor_name")

            # 4. Description match (Exact, substring, and compact stripped)
            for desc in doc.descriptions:
                desc_lower = desc.lower()
                desc_compact = re.sub(r"[^a-z0-9\u0E00-\u0E7F]", "", desc_lower)
                if q_clean in desc_lower:
                    bonus += 6.0
                    fields.add("description")
                elif q_compact and desc_compact and len(q_compact) >= 4 and (q_compact in desc_compact or desc_compact in q_compact):
                    bonus += 7.0
                    fields.add("compact_description_match")

            if bonus > 0:
                scores[qid] = scores.get(qid, 0.0) + bonus
                matched_fields_map[qid] = fields


        if not scores:
            return []

        # Normalize BM25 scores between [0.0, 1.0] using min-max sigmoid scaling
        max_score = max(scores.values())
        results: List[BM25SearchResult] = []
        for qid, raw_score in scores.items():
            # Normalized score: map raw score to 0.70 - 0.99 for strong matches
            normalized_score = min(0.99, max(0.50, 0.50 + 0.49 * (raw_score / (max_score + 1e-5))))
            results.append(
                BM25SearchResult(
                    quotation_id=qid,
                    score=round(normalized_score, 4),
                    matched_terms=sorted(list(matched_terms_map.get(qid, []))),
                    matched_fields=sorted(list(matched_fields_map.get(qid, []))),
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
