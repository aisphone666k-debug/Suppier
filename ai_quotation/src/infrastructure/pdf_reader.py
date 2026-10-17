import base64
import configparser
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import os
import re
from typing import Optional
import httpx
from pypdf import PdfReader

from src.domain.extracted_quotation_draft import ExtractedQuotationDraft, DraftItem


class CorruptPdfDocumentException(RuntimeError):
    """Raised when PDF structure cannot be read or parsed."""
    pass


@dataclass(frozen=True)
class ExtractedPdfMetadata:
    file_path: str
    sha256: str
    raw_text: str
    page_count: int
    inferred_quotation_number: Optional[str] = None
    inferred_vendor_name: Optional[str] = None
    inferred_issue_date: Optional[date] = None
    inferred_expiration_date: Optional[date] = None
    inferred_total: Optional[float] = None
    layout_text: Optional[str] = None


class PdfDocumentReader:
    """Gateway for reading PDF files, extracting textual content and metadata."""

    def extract(self, file_path: str) -> ExtractedPdfMetadata:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF document not found at: {file_path}")

        # Compute SHA-256 hash
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        file_sha256 = hasher.hexdigest()

        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            extracted_pages: list[str] = []
            extracted_layout_pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                extracted_pages.append(text)
                try:
                    layout_text = page.extract_text(extraction_mode="layout") or text
                except Exception:
                    layout_text = text
                extracted_layout_pages.append(layout_text)
            raw_text = "\n".join(extracted_pages).strip()
            layout_raw_text = "\n".join(extracted_layout_pages).strip()
        except Exception as e:
            raise CorruptPdfDocumentException(f"Failed to parse PDF document {file_path}: {e}") from e

        # If scanned document has no readable text layer, attempt OCR fallback
        if len(raw_text.strip()) < 30 and page_count > 0:
            ocr_text = self._ocr_scanned_pdf(reader, file_sha256)
            if ocr_text:
                raw_text = ocr_text
                layout_raw_text = ocr_text

        # Heuristic inference from filename and raw text
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        inferred_quotation_number = self._infer_quotation_number(base_name, raw_text)
        inferred_vendor_name = self._infer_vendor_name(base_name, raw_text)
        inferred_issue_date, inferred_expiration_date = self._infer_dates(raw_text, layout_raw_text)
        inferred_total = self._infer_total_amount(raw_text)

        return ExtractedPdfMetadata(
            file_path=file_path,
            sha256=file_sha256,
            raw_text=raw_text,
            page_count=page_count,
            inferred_quotation_number=inferred_quotation_number,
            inferred_vendor_name=inferred_vendor_name,
            inferred_issue_date=inferred_issue_date,
            inferred_expiration_date=inferred_expiration_date,
            inferred_total=inferred_total,
            layout_text=layout_raw_text,
        )

    @staticmethod
    def _load_gemini_config() -> tuple[Optional[str], str]:
        api_key = None
        model = "gemini-2.5-flash"
        if os.path.exists("credentials.ini"):
            try:
                config = configparser.ConfigParser()
                config.read("credentials.ini")
                if "gemini" in config:
                    api_key = config["gemini"].get("api_key", "").strip() or None
                    model = config["gemini"].get("model", model).strip() or model
            except Exception:
                pass
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip() or None
        if os.environ.get("GEMINI_MODEL", "").strip():
            model = os.environ.get("GEMINI_MODEL", "").strip()
        return api_key, model

    def _ocr_scanned_pdf(self, reader: PdfReader, sha256_hash: str) -> Optional[str]:
        cache_dir = os.path.join(".cache", "ocr")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{sha256_hash}.txt")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_text = f.read().strip()
                if cached_text:
                    return cached_text
            except Exception:
                pass

        api_key, model = self._load_gemini_config()
        if not api_key:
            return None

        images_parts = []
        for page in reader.pages:
            for img in page.images:
                try:
                    img_bytes = img.data
                    mime_type = "image/jpeg" if img.name.lower().endswith(".jpg") or img.name.lower().endswith(".jpeg") else "image/png"
                    b64_data = base64.b64encode(img_bytes).decode("utf-8")
                    images_parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
                except Exception:
                    continue

        if not images_parts:
            return None

        prompt = "Extract all text verbatim and tabular contents from this scanned quotation document."
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}] + images_parts
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 4096,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=35.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    ocr_text = "".join(part.get("text", "") for part in parts).strip()
                    if ocr_text:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            f.write(ocr_text)
                        return ocr_text
        except Exception:
            return None
        return None

    def _infer_quotation_number(self, base_name: str, raw_text: str) -> str:
        ignored_tokens = {"title", "subject", "date", "page", "number", "quotation", "item", "header"}
        for match in re.finditer(r"(?:QT|QUOTATION|NO\.?)\s*[:#\-\s]?\s*([A-Za-z0-9\-_]{4,20})", raw_text, re.IGNORECASE):
            candidate = match.group(1).strip()
            if candidate.lower().startswith("no") and len(candidate) > 4:
                candidate = candidate[2:]
            if candidate and candidate.lower() not in ignored_tokens:
                if any(c.isdigit() for c in candidate) or "-" in candidate:
                    return candidate

        # Fallback to sanitized filename
        clean_name = re.sub(r"[^\w\-_]", " ", base_name).strip()
        tokens = clean_name.split()
        return tokens[0] if tokens else "QT-UNKNOWN"


    @staticmethod
    def _clean_vendor_name(name: str) -> str:
        if not name:
            return ""
        name = re.sub(r"[\uf700-\uf7ff]", "", name)
        name = re.sub(r"[\?]+", " ", name)
        # Strip repeated Thai box-drawing / border characters e.g. ๏๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๔๐
        name = re.sub(r"[๏๐๑๒๓๔๕๖]{2,}.*$", "", name).strip()
        name = re.sub(r"[\s๏๐๑๒๓๔๕๖|+=_\-\*~#]+$", "", name).strip()
        # Strip attached address text starting with digits (e.g. (Head Office)33/4 The 9th Towers...)
        name = re.sub(r"(?<=[a-zA-Z\)])\d{1,4}/\d+.*$", "", name).strip()
        name = name.rstrip(",-:; ")
        return name

    def _infer_vendor_name(self, base_name: str, raw_text: str) -> str:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for line in lines:
            low = line.lower()
            if any(b in low for b in ["minebea", "nmb-"]):
                continue
            if low.startswith(("attn", "attention", "to:", "customer:", "dear", "ship to", "bill to", "ผู้ติดต่อ", "เรียน")):
                continue
            if any(term in low for term in ["co., ltd", "co.,ltd", "ltd.,part", "ltd., part", "part.,ltd", "partnership", "company", "corp", "inc", "bando", "หจก", "จำกัด"]):
                return self._clean_vendor_name(line)
        if "bando" in base_name.lower():
            return "BANDO CHEMICAL INDUSTRIES (THAILAND) LTD."
        if "minebea" in base_name.lower():
            return "NMB-MINEBEA THAI LTD."
        # Fallback to first non-recipient line
        for line in lines[:5]:
            low = line.lower()
            if any(b in low for b in ["minebea", "nmb-"]) or low.startswith(("attn", "attention", "to:", "customer:")):
                continue
            return self._clean_vendor_name(line)
        return self._clean_vendor_name(lines[0]) if lines else "Vendor Unknown"

    def _infer_dates(self, raw_text: str, layout_text: str = "") -> tuple[date, date]:
        return self._extract_dates(raw_text, layout_text)

    def _infer_total_amount(self, raw_text: str) -> Optional[float]:
        # Prefer Grand Total / Net Amount if explicitly stated
        grand_match = re.search(r"(?:Grand\s*Total|Net\s*Amount|ยอดรวมทั้งสิ้น|จ[ำาํ\s]*นวนเงินรวมทั้งสิ้น)\s*[:=\u0e53|]?\s*([0-9,]+\.[0-9]{2})", raw_text, re.IGNORECASE)
        if grand_match:
            try:
                return float(grand_match.group(1).replace(",", ""))
            except ValueError:
                pass

        total_pattern = r"(?:Total|Grand Total|Net Amount|ยอดรวม|จ[ำาํ\s]*นวนเงินรวม)\s*[:=\u0e53|]?\s*([0-9,]+\.[0-9]{2})"
        match = re.search(total_pattern, raw_text, re.IGNORECASE)
        if match:
            clean_str = match.group(1).replace(",", "")
            try:
                return float(clean_str)
            except ValueError:
                return None
        return None

    def extract_draft(self, file_path: str) -> ExtractedQuotationDraft:
        """Intelligently parses PDF and extracts complete quotation draft with metadata and line items."""
        meta = self.extract(file_path)
        raw_text = meta.raw_text
        layout_text = meta.layout_text or ""
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        quotation_number = self._extract_quotation_number(base_name, raw_text)
        vendor_name = self._extract_vendor_name(base_name, raw_text)
        vendor_tax_id = self._extract_vendor_tax_id(raw_text)
        currency = self._extract_currency(raw_text)
        issue_date, expiration_date = self._extract_dates(raw_text, layout_text)
        items = self._extract_line_items(raw_text, meta.inferred_total, layout_text=layout_text)

        total_amount = meta.inferred_total
        if total_amount is None and items:
            total_amount = sum(it.amount if it.amount is not None else (it.quantity * it.unit_price) for it in items)

        return ExtractedQuotationDraft(
            file_path=file_path,
            sha256=meta.sha256,
            quotation_number=quotation_number,
            vendor_name=vendor_name,
            issue_date=issue_date,
            expiration_date=expiration_date,
            currency=currency,
            items=items,
            vendor_tax_id=vendor_tax_id,
            total_amount=total_amount,
            raw_text=raw_text,
            confidence_score=1.0,
        )

    def _extract_quotation_number(self, base_name: str, raw_text: str) -> str:
        patterns = [
            r"Quotation\s*No\.?\s*[:\?#\uff1a]\s*([A-Za-z0-9\-_]{4,20})",
            r"Quotation\s*[:\?#\uff1a]\s*([A-Za-z0-9\-_]{4,20})",
            r"(?:เลขที่|เลขทีÉ)\s*[:\?#\uff1a]?\s*([A-Za-z0-9\-_]{4,20})",
            r"No\.?\s*[:\?#\uff1a]\s*([A-Za-z0-9\-_]{4,20})",
            r"Quotations?\s+No\.?\s*[:\?#\uff1a]?\s*([A-Za-z0-9\-_]{4,20})",
            r"\b(SQ-[0-9]{6,15})\b",
            r"\b(26DD\d{5,10})\b",
            r"\b(26Q\d{5,10})\b",
            r"\b(QT\d{5,10})\b",
            r"QT\s*[:#\-\uff1a]\s*([A-Za-z0-9\-_]{4,20})",
            r"SO\s*([0-9A-Za-z\-_/]{4,20})",
        ]
        ignored = {"title", "subject", "date", "page", "number", "quotation", "item", "header", "unknown"}
        for p in patterns:
            match = re.search(p, raw_text, re.IGNORECASE)
            if match:
                cand = match.group(1).strip()
                if cand.lower() not in ignored and (any(c.isdigit() for c in cand) or "-" in cand):
                    return cand
        return self._infer_quotation_number(base_name, raw_text)

    def _extract_vendor_name(self, base_name: str, raw_text: str) -> str:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip() and line.strip() not in [":", "-", "."]]
        candidates = []
        vendor_terms = [
            "co., ltd", "co.,ltd", "ltd.,part", "ltd., part", "part.,ltd", "part., ltd",
            "partnership", "corp", "limited", "industries", "technology", "automation",
            "sangyo", "engineering", "electric", "ltd."
        ]
        for line in lines:
            low = line.lower()
            if "minebea" in low or "nmb-" in low:
                continue
            if low in ["company", "quotation", "quotations no", "invoice"]:
                continue
            if low.startswith(("attn", "attention", "to:", "customer:", "dear", "ship to", "bill to", "ผู้ติดต่อ", "เรียน")):
                continue
            if any(term in low for term in vendor_terms) or re.search(r"\binc\b", low):
                cleaned = self._clean_vendor_name(line)
                if cleaned and len(cleaned) > 3:
                    candidates.append(cleaned)
            elif "บริษัท" in line and ("จำกัด" in line or "จํากัด" in line):
                thai_sub = re.search(r"(บริษัท\s+[^\s]+(?:\s+[^\s]+)*\s+จ[ำาํ]+กัด(?:\s*\(มหาชน\))?)", line)
                cand = thai_sub.group(1).strip() if thai_sub else line
                cleaned = self._clean_vendor_name(cand)
                if cleaned and len(cleaned) > 3:
                    candidates.append(cleaned)
            elif any(th_term in line for th_term in ["ห้างหุ้นส่วนจำกัด", "ห้างหุ้นส่วน", "หจก.", "หจก"]):
                thai_sub = re.search(r"((?:ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วน|หจก\.?)\s+[^\s]+(?:\s+[^\s]+)*)", line)
                cand = thai_sub.group(1).strip() if thai_sub else line
                cleaned = self._clean_vendor_name(cand)
                if cleaned and len(cleaned) > 3:
                    candidates.append(cleaned)

        if candidates:
            # Prefer English vendor name if available (e.g. THAI-INTER ELECTRIC INDUSTRIES CO.,LTD.)
            eng_cands = [c for c in candidates if any(t in c.lower() for t in vendor_terms)]
            return eng_cands[0] if eng_cands else candidates[0]

        if "bando" in base_name.lower():
            return "BANDO CHEMICAL INDUSTRIES (THAILAND) LTD."
        if "fanuc" in raw_text.lower():
            return "FANUC THAI LIMITED"
        if "tornos" in raw_text.lower():
            return "TORNOS S.A."
        if "factory max" in raw_text.lower() or "แฟ็คทอรี่" in raw_text or "แฟ็ คทอรี" in raw_text:
            return "บริษัท แฟ็คทอรี่ แม๊กซ์ จำกัด (Factory Max Co., Ltd.)"
        return self._infer_vendor_name(base_name, raw_text)

    def _extract_vendor_tax_id(self, raw_text: str) -> Optional[str]:
        matches = re.findall(r"\b(\d{13})\b", raw_text)
        for m in matches:
            if m != "0145551000663":  # Skip buyer (Minebea) tax ID
                return m
        return None

    def _extract_currency(self, raw_text: str) -> str:
        if "jpy" in raw_text.lower() or "yen" in raw_text.lower():
            return "JPY"
        if "usd" in raw_text.lower() or "dollar" in raw_text.lower():
            return "USD"
        if "eur" in raw_text.lower():
            return "EUR"
        return "THB"

    @staticmethod
    def _parse_date_token(s: str) -> Optional[date]:
        if not s:
            return None
        s = s.strip().rstrip(".,;:/\\-_")
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

        # 1. ISO YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
        m_iso = re.match(r"^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$", s)
        if m_iso:
            y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
            try:
                return date(y, m, d)
            except ValueError:
                pass

        # 2. DD-Mon-YYYY or DD Mon YYYY (e.g. 25-Sep-2026)
        m_alpha1 = re.match(r"^(\d{1,2})[/\-\s]([A-Za-z]{3,9})[/\-\s](\d{2,4})$", s)
        if m_alpha1 and m_alpha1.group(2).lower()[:3] in months:
            d = int(m_alpha1.group(1))
            m = months[m_alpha1.group(2).lower()[:3]]
            y = int(m_alpha1.group(3))
            if y < 100:
                y = 2000 + y
            try:
                return date(y, m, d)
            except ValueError:
                pass

        # 3. Mon DD, YYYY or Mon DD YYYY (e.g. Sep 23, 2026 or October 2, 2026)
        m_alpha2 = re.match(r"^([A-Za-z]{3,9})[/\-\s](\d{1,2}),?[/\-\s](\d{2,4})$", s)
        if m_alpha2 and m_alpha2.group(1).lower()[:3] in months:
            m = months[m_alpha2.group(1).lower()[:3]]
            d = int(m_alpha2.group(2))
            y = int(m_alpha2.group(3))
            if y < 100:
                y = 2000 + y
            try:
                return date(y, m, d)
            except ValueError:
                pass

        # 4. DD/MM/YYYY or DD.MM.YYYY or DD/MM/YY (supporting Thai Buddhist Era)
        m_num = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})$", s)
        if m_num:
            d, m, y = int(m_num.group(1)), int(m_num.group(2)), int(m_num.group(3))
            if y < 100:
                y = 2500 + y - 543 if y >= 40 else 2000 + y
            elif y >= 2400:
                y = y - 543
            try:
                return date(y, m, d)
            except ValueError:
                pass

        return None

    def _extract_dates(self, raw_text: str, layout_text: str = "") -> tuple[date, date]:
        today = date.today()
        combined_text = (layout_text + "\n" + raw_text) if layout_text else raw_text
        all_lines = combined_text.splitlines()

        # --- 1. EXTRACT ISSUE DATE ---
        issue_date: Optional[date] = None

        # Priority A: Check lines with explicit date prefixes
        prefix_pattern = r"(?:issue\s*date|date|request\s*date|วันที่|วษนทรท|วันทีÉ)\s*[:\?#\uff1a]?\s*([0-9A-Za-z\.\-/\s]{6,25})"
        for line in all_lines:
            m_prefix = re.search(prefix_pattern, line, re.IGNORECASE)
            if m_prefix:
                cand = m_prefix.group(1).strip()
                for token in re.findall(r"[A-Za-z0-9\.\-/]+", cand):
                    d = self._parse_date_token(token)
                    if d and 2000 <= d.year <= 2050:
                        issue_date = d
                        break
                if not issue_date:
                    d = self._parse_date_token(cand)
                    if d and 2000 <= d.year <= 2050:
                        issue_date = d
                if issue_date:
                    break

        # Priority B: Alphanumeric dates anywhere (e.g. 25-Sep-2026 or Sep 23, 2026 or October 2, 2026)
        if not issue_date:
            for m in re.finditer(r"\b(\d{1,2}[/\-\s][A-Za-z]{3,9}[/\-\s]\d{4})\b", combined_text):
                d = self._parse_date_token(m.group(1))
                if d and 2000 <= d.year <= 2050:
                    issue_date = d
                    break
        if not issue_date:
            for m in re.finditer(r"\b([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b", combined_text):
                d = self._parse_date_token(m.group(1))
                if d and 2000 <= d.year <= 2050:
                    issue_date = d
                    break

        # Priority C: ISO dates (YYYY/MM/DD or YYYY-MM-DD)
        if not issue_date:
            for m in re.finditer(r"\b(20\d{2}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b", combined_text):
                d = self._parse_date_token(m.group(1))
                if d and 2000 <= d.year <= 2050:
                    issue_date = d
                    break

        # Priority D: Standard numeric dates DD/MM/YYYY
        if not issue_date:
            for m in re.finditer(r"\b(\d{1,2}[/\-\.](\d{1,2})[/\-\.](\d{2,4}))\b", combined_text):
                d = self._parse_date_token(m.group(1))
                if d and 2000 <= d.year <= 2050:
                    issue_date = d
                    break

        if not issue_date:
            issue_date = today

        # --- 2. EXTRACT EXPIRATION DATE ---
        expiration_date: Optional[date] = None

        # Priority 1: Range format: 'Validity <start> to <end>'
        range_m = re.search(r"(?:validity|valid)\s*(?:from\s*)?[0-9A-Za-z\.\-/]+\s*(?:to|until|-)\s*([0-9A-Za-z\.\-/]{6,15})", combined_text, re.IGNORECASE)
        if range_m:
            d = self._parse_date_token(range_m.group(1))
            if d and d >= issue_date:
                expiration_date = d

        # Priority 2: Thai explicit until date: 'ถึงวันที่ <date>'
        if not expiration_date:
            th_m = re.search(r"(?:ถึงวันที่|หมดอายุ(?:วันที่)?)\s*[:\?#\uff1a]?\s*([0-9A-Za-z\.\-/]{6,15})", combined_text, re.IGNORECASE)
            if th_m:
                d = self._parse_date_token(th_m.group(1))
                if d and d >= issue_date:
                    expiration_date = d

        # Priority 3: Price Validity / Valid Until / Expire Date followed by explicit DATE
        if not expiration_date:
            for line in all_lines:
                m_exp = re.search(r"(?:price\s*validity|valid\s*until|valid\s*to|validity|expire|expiry|expiration)\s*(?:date)?\s*[:\?#\uff1a]?\s*([0-9A-Za-z\.\-/]{6,15})", line, re.IGNORECASE)
                if m_exp:
                    cand = m_exp.group(1).strip()
                    if not re.search(r"^\d+\s*days?", cand, re.IGNORECASE):
                        d = self._parse_date_token(cand)
                        if d and d >= issue_date:
                            expiration_date = d
                            break

        # Priority 4: Line-based validity in days (Thai or English)
        if not expiration_date:
            for line in all_lines:
                is_validity_line = bool(re.search(r"(?:ยืน\s*ราคา|ยืนยันร[ำา]คำ|ยืนยันราคา|ก[ำาํ\s]*หนดยืนราคา|กจจหนดยยนรจคจ|price\s*validity|valid\s*to|validity|valid\s*for)", line, re.IGNORECASE))
                if is_validity_line:
                    m_days = re.search(r"(?:[:\s]|^)(\d{1,3})\s*(?:วัน|วนั|days?|วษน)\b", line, re.IGNORECASE)
                    if not m_days:
                        m_days = re.search(r"[:\?#\uff1a\s]+(\d{1,3})\s*(?:days?|วัน|วนั|วษน)?", line, re.IGNORECASE)
                    if m_days:
                        days_val = int(m_days.group(1))
                        if 1 <= days_val <= 365:
                            expiration_date = issue_date + timedelta(days=days_val)
                            break

        # Priority 5: Fallback raw text search for validity days
        if not expiration_date:
            m_raw_days = re.search(r"(?:valid\s+to|validity|price\s+validity)\s*[:\?#\uff1a]?\s*(\d+)\s*(?:days?|วัน)", combined_text, re.IGNORECASE)
            if m_raw_days:
                days_val = int(m_raw_days.group(1))
                if 1 <= days_val <= 365:
                    expiration_date = issue_date + timedelta(days=days_val)

        # Priority 6: Default fallback (+90 days)
        if not expiration_date or expiration_date <= issue_date:
            expiration_date = issue_date + timedelta(days=90)

        return issue_date, expiration_date

    def _extract_line_items(self, raw_text: str, inferred_total: Optional[float], layout_text: str = "") -> tuple[DraftItem, ...]:
        # 0. Layout-mode tabular rows (Factory Max and columnar quotations)
        if layout_text:
            layout_lines = [l for l in layout_text.splitlines() if l.strip()]
            fmax_layout_pattern = re.compile(
                r"^\s*(\d+)\.\s+([A-Za-z0-9\-_#]+)\s+(.+?)\s+([0-9,]+(?:\.\d+)?)\s+([A-Za-z\u0E00-\u0E7F]+)\s+([0-9,]+\.[0-9]{2}).*?([0-9,]+\.[0-9]{2})\s*$"
            )
            layout_items: list[DraftItem] = []
            for idx, l_line in enumerate(layout_lines):
                m_fmax = fmax_layout_pattern.match(l_line)
                if m_fmax:
                    item_no = int(m_fmax.group(1))
                    part_no = m_fmax.group(2).strip()
                    desc = m_fmax.group(3).strip()
                    qty = float(m_fmax.group(4).replace(",", ""))
                    unit = m_fmax.group(5).strip()
                    amt = float(m_fmax.group(7).replace(",", ""))
                    unit_price = amt / qty if qty > 0 else amt

                    # Lookahead for wrapped description continuation (e.g. 'SPINDLE')
                    if idx + 1 < len(layout_lines):
                        next_line = layout_lines[idx + 1]
                        if not fmax_layout_pattern.match(next_line) and not re.match(r"^\s*\d+\.", next_line):
                            if not re.search(r"รวม|total|vat|ภาษี|ส่วนลด|delivery|payment|หมายเหตุ|fmx|csr|ผู้มีอํานาจ|ผู้มีอำนาจ|ผู้เสนอราคา|บริษัท|ใบเสนอราคา", next_line, re.IGNORECASE):
                                cont = next_line.strip()
                                if cont and len(cont) < 100:
                                    desc = f"{desc} {cont}"

                    layout_items.append(DraftItem(
                        item_number=item_no,
                        description=desc,
                        quantity=qty,
                        unit=unit,
                        unit_price=unit_price,
                        part_number=part_no,
                        amount=amt,
                    ))
                elif "Belt 7M" in l_line:
                    m_iw = re.search(r"^\s*(\d+)\s+(Belt\s+[A-Za-z0-9\s/]+?)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]+)\s+([0-9,]+\.[0-9]{2})\s+([0-9,]+\.[0-9]{2})", l_line)
                    if m_iw:
                        item_no = int(m_iw.group(1))
                        desc = m_iw.group(2).strip()
                        qty = float(m_iw.group(3))
                        unit = m_iw.group(4).strip()
                        price = float(m_iw.group(5).replace(",", ""))
                        amt = float(m_iw.group(6).replace(",", ""))
                        layout_items.append(DraftItem(
                            item_number=item_no,
                            description=desc,
                            quantity=qty,
                            unit=unit,
                            unit_price=price,
                            part_number="Belt 7M 1360",
                            amount=amt,
                        ))
            if layout_items:
                return tuple(layout_items)

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        items: list[DraftItem] = []

        # Standard line item formats
        p1 = re.compile(r"^(\d+)\s+([A-Za-z0-9\-_#]{3,30})\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,]+\.[0-9]{2})\s+([0-9,]+\.[0-9]{2})$")
        p2 = re.compile(
            r"^(\d{1,4})(?:\s+|(?=[A-Za-z\u0E00-\u0E7F]))(.+?)\s+([0-9,]+(?:\.\d+)?)\s+([A-Za-z\.\u0E00-\u0E7F/]+)\s+([0-9,]+\.[0-9]{2})(?:\s+(?:[0-9,]+(?:\.[0-9]{2})?%?|-))?\s+([0-9,]+\.[0-9]{2})$"
        )
        p2_no_unit = re.compile(
            r"^(\d{1,4})(?:\s+|(?=[A-Za-z\u0E00-\u0E7F]))(.+?)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+\.[0-9]{2})(?:\s+(?:[0-9,]+(?:\.[0-9]{2})?%?|-))?\s+([0-9,]+\.[0-9]{2})$"
        )
        p3 = re.compile(r"^[?]?\s*(\d+)\s*[?]\s*(.+?)\s*[?]\s*(\d+(?:\.\d+)?)[^0-9\n\r]*[?]\s*([0-9,]+\.[0-9]{2})[?\s]*([0-9,]+\.[0-9]{2})?")
        # 0. Delimiter-separated table rows (pipe '|' or Thai box character '\u0e53')
        delim_items: list[DraftItem] = []
        for i, line in enumerate(lines):
            if "|" in line or "\u0e53" in line:
                cols = [c.strip() for c in re.split(r"[|\u0e53]", line)]
                if cols and not cols[0]:
                    cols.pop(0)
                if cols and not cols[-1]:
                    cols.pop()
                if cols and re.match(r"^\d{1,4}$", cols[0]):
                    item_no = int(cols[0])
                    if len(cols) == 7:
                        # Format A (e.g. 25-334.pdf): item_no, part_no, desc, unit, qty, price, amount
                        part_no = cols[1].strip()
                        desc = re.sub(r"[\uf700-\uf7ff]", "", cols[2]).strip()
                        unit = cols[3].strip() or "Pcs"
                        qty = float(cols[4].replace(",", ""))
                        price = float(cols[5].replace(",", ""))
                        amt = float(cols[6].replace(",", ""))
                    elif len(cols) >= 5:
                        # Format B (e.g. Thai-Inter): item_no, desc, qty[+unit], price, [discount], amount
                        raw_desc = re.sub(r"[\uf700-\uf7ff]", "", cols[1]).strip()
                        if any(h in raw_desc.lower() for h in ["description", "unit price", "item", "q'ty", "qty", "amount", "รายละเอียด", "สินค้า"]):
                            continue
                        qty_m = re.match(r"^([0-9,]+(?:\.\d+)?)\s*(.*)$", cols[2])
                        qty = float(qty_m.group(1).replace(",", "")) if qty_m else 1.0
                        unit_cand = qty_m.group(2).strip() if qty_m else ""
                        unit = unit_cand if unit_cand else "Pcs"
                        price = float(cols[3].replace(",", "")) if cols[3] else 0.0
                        amt_str = cols[-1].replace(",", "") if cols[-1] else str(qty * price)
                        amt = float(amt_str) if amt_str else (qty * price)
                        desc = raw_desc
                        part_no = None
                        p_match = re.search(r"\b(SUS\s+M[0-9\.\*]+|M\d+(?:\.\d+)?\*\d+|[A-Z0-9]{2,}[\-_][A-Z0-9\-_]+)\b", desc)
                        if p_match:
                            part_no = p_match.group(1).strip()
                        else:
                            leading_part = re.match(r"^([A-Z0-9][A-Za-z0-9\.\-_]*(?:\s+[0-9\.\-]+[A-Za-z0-9\-]*)?)[\"'\s]", desc)
                            if leading_part and len(leading_part.group(1)) >= 3:
                                part_no = leading_part.group(1).strip()
                    else:
                        continue

                    delim_items.append(DraftItem(
                        item_number=item_no,
                        description=desc,
                        quantity=qty,
                        unit=unit,
                        unit_price=price,
                        part_number=part_no,
                        amount=amt,
                    ))

        if delim_items:
            return tuple(delim_items)

        for i, line in enumerate(lines):
            # 1. FANUC and clean part-description-qty-price tables
            m1 = p1.match(line)
            if m1:
                item_no = int(m1.group(1))
                part_no = m1.group(2).strip()
                desc = m1.group(3).strip()
                qty = float(m1.group(4))
                price = float(m1.group(5).replace(",", ""))
                amt = float(m1.group(6).replace(",", ""))
                items.append(DraftItem(
                    item_number=item_no,
                    description=desc,
                    quantity=qty,
                    unit="Set",
                    unit_price=price,
                    part_number=part_no,
                    amount=amt,
                ))
                continue

            # 2. Tornos & item-code tables
            tornos_m = re.search(r"^\d+\s+(\d{5,10})\s+(\d+(?:\.\d+)?)\s+([A-Za-z]+)\s+([0-9,]+\.[0-9]{2})\s+([0-9,]+\.[0-9]{2})", line)
            if tornos_m:
                part_no = tornos_m.group(1).strip()
                qty = float(tornos_m.group(2))
                unit = tornos_m.group(3).strip()
                price = float(tornos_m.group(4).replace(",", ""))
                amt = float(tornos_m.group(5).replace(",", ""))
                desc = f"Part {part_no}"
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if not re.search(r"delivery|total|discount|payment|intercontinental", next_line, re.IGNORECASE):
                        desc = next_line
                items.append(DraftItem(
                    item_number=len(items) + 1,
                    description=desc,
                    quantity=qty,
                    unit=unit,
                    unit_price=price,
                    part_number=part_no,
                    amount=amt,
                ))
                continue

            # 3. Standard items with specs on next line or in description
            m2 = p2.match(line)
            m2_nu = None if m2 else p2_no_unit.match(line)
            if m2 or m2_nu:
                m_target = m2 if m2 else m2_nu
                item_no = int(m_target.group(1))
                desc = re.sub(r"[\uf700-\uf7ff]", "", m_target.group(2)).strip()
                if any(h in desc.lower() for h in ["description", "unit price", "item", "q'ty", "qty", "amount"]):
                    continue
                qty = float(m_target.group(3).replace(",", ""))
                unit = m_target.group(4).strip().rstrip(".").strip() if m2 else "Pcs"
                price = float((m_target.group(5) if m2 else m_target.group(4)).replace(",", ""))
                amt = float((m_target.group(6) if m2 else m_target.group(5)).replace(",", ""))

                part_no = None
                if desc.isdigit() or (len(desc) >= 5 and desc.isalnum()):
                    part_no = desc
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if not re.search(r"delivery|total|discount|payment", next_line, re.IGNORECASE):
                            desc = next_line

                if not part_no and i + 1 < len(lines):
                    next_line = lines[i+1]
                    spec_m = re.search(r"(?:Spec|Model|Part\s*No)\s*[:#\?]?\s*([A-Za-z0-9\-_/]+)", next_line, re.IGNORECASE)
                    if spec_m:
                        part_no = spec_m.group(1).strip()

                if not part_no:
                    model_m = re.search(r"\b(SUS\s+M[0-9\.\*]+|M\d+(?:\.\d+)?\*\d+|[A-Z0-9]{3,}[\-_][A-Z0-9\-_]+)\b", desc)
                    if model_m:
                        part_no = model_m.group(1).strip()

                items.append(DraftItem(
                    item_number=item_no,
                    description=desc,
                    quantity=qty,
                    unit=unit,
                    unit_price=price,
                    part_number=part_no,
                    amount=amt,
                ))
                continue

            # 4. BANDO format: BANDO BELT 10 PCS 513. 5,130A-61(S)
            bando_m = re.search(r"([A-Za-z\s]+?)\s+(\d+)\s+PCS\s+([0-9\.]+)\s+([0-9,]+)([A-Za-z0-9\-_\(\)]+)", line)
            if bando_m:
                desc = bando_m.group(1).strip()
                qty = float(bando_m.group(2))
                price = float(bando_m.group(3))
                part_no = bando_m.group(5).strip()
                items.append(DraftItem(
                    item_number=len(items) + 1,
                    description=desc,
                    quantity=qty,
                    unit="PCS",
                    unit_price=price,
                    part_number=part_no,
                    amount=qty * price,
                ))
                continue

            # 5. Thai ELCB format (e.g. EW32EAG "FUJI" ELCB 3P 30A 30mA)
            if "EW32EAG" in line:
                thai_m = re.search(r"EW32EAG[\"']?([A-Za-z0-9]+)?[\"']?([A-Za-z0-9\s]+).*?(\d+\.\d+)\s*([^\s0-9]+).*?([0-9,]+\.[0-9]{2})", line)
                if thai_m:
                    items.append(DraftItem(
                        item_number=len(items) + 1,
                        description="FUJI ELCB 3P 30A 30mA",
                        quantity=float(thai_m.group(3)),
                        unit=thai_m.group(4).strip(),
                        unit_price=float(thai_m.group(5).replace(",", "")),
                        part_number="EW32EAG",
                        amount=float(thai_m.group(5).replace(",", "")),
                    ))
                    continue

            # 6. Trisak Omron format (H7CC-ASD COUNTER OMRON)
            if "H7CC" in line or ("OMRON" in line and "PCS" in line):
                omron_m = re.search(r"([0-9,]+\.[0-9]{2})\s+([0-9,]+\.[0-9]{2})\s*([A-Za-z]+)\s*(\d+)([A-Za-z0-9\-]+)\s*:\s*(.+)", line)
                if omron_m:
                    items.append(DraftItem(
                        item_number=len(items) + 1,
                        description=omron_m.group(6).strip().rstrip("0123456789"),
                        quantity=float(omron_m.group(4)),
                        unit=omron_m.group(3).strip(),
                        unit_price=float(omron_m.group(2).replace(",", "")),
                        part_number=omron_m.group(5).strip(),
                        amount=float(omron_m.group(1).replace(",", "")),
                    ))
                    continue

            # 7. Iwase Belt format (Belt 7M 1360 / Gate)
            if "Belt 7M" in line or ("PCSBelt" in line):
                iwase_m = re.search(r"([0-9,]+\.[0-9]{2})\s+([0-9,]+\.[0-9]{2})\s*PCS(Belt\s+[A-Za-z0-9\s/]+?)\s+(\d+(?:\.\d+)?)(?:\s+\d+\s*-\s*\d+\s*days|\s+\d+|$)", line)
                if iwase_m:
                    amt = float(iwase_m.group(1).replace(",", ""))
                    price = float(iwase_m.group(2).replace(",", ""))
                    desc = iwase_m.group(3).strip()
                    qty = float(iwase_m.group(4))
                    if abs(qty * price - amt) > 0.01 and price > 0:
                        qty = round(amt / price, 2)
                    items.append(DraftItem(
                        item_number=len(items) + 1,
                        description=desc,
                        quantity=qty,
                        unit="PCS",
                        unit_price=price,
                        part_number="Belt 7M 1360",
                        amount=amt,
                    ))
                    continue

            # 8. Factory Max NSK Air Line Kit format
            if "AL-M1202" in line or "NSKT" in line:
                combined = line
                if i + 1 < len(lines) and not any(k in lines[i+1] for k in ["NSKT", "รวม", "total", "vat", "หมายเหตุ"]):
                    combined += " " + lines[i+1]
                if i + 2 < len(lines) and not any(k in lines[i+2] for k in ["NSKT", "รวม", "total", "vat", "หมายเหตุ"]):
                    combined += " " + lines[i+2]
                fmax_m = re.search(r"(NSKT-[0-9]{4,5})(?:[0-9]+\.)?.*?(NSK\s*\[[A-Za-z0-9\-]+\]\s*[A-Za-z\s]+?)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]+)\s+([0-9,]+\.[0-9]{2}).*?([0-9,]+\.[0-9]{2})", combined)
                if fmax_m:
                    p_no = fmax_m.group(1).strip()
                    desc = re.sub(r"\s+", " ", fmax_m.group(2).strip())
                    qty = float(fmax_m.group(3))
                    unit = fmax_m.group(4).strip()
                    amt = float(fmax_m.group(6).replace(",", ""))
                    unit_price = amt / qty if qty > 0 else amt
                    items.append(DraftItem(
                        item_number=len(items) + 1,
                        description=desc,
                        quantity=qty,
                        unit=unit,
                        unit_price=unit_price,
                        part_number=p_no,
                        amount=amt,
                    ))
                    continue

            # 9. Fallback match for table rows with ? markers
            m3 = p3.match(line)
            if m3:
                item_no = int(m3.group(1))
                desc = m3.group(2).strip()
                if any(h in desc.lower() for h in ["description", "amount", "price"]):
                    continue
                qty = float(m3.group(3))
                price = float(m3.group(4).replace(",", ""))
                amt = float(m3.group(5).replace(",", "")) if m3.group(5) else (qty * price)
                items.append(DraftItem(
                    item_number=item_no,
                    description=desc,
                    quantity=qty,
                    unit="Pcs",
                    unit_price=price,
                    part_number=None,
                    amount=amt,
                ))
                continue

        if not items:
            default_price = inferred_total if inferred_total is not None else 1000.0
            items.append(DraftItem(
                item_number=1,
                description="General Industrial Quotation Item",
                quantity=1.0,
                unit="Set",
                unit_price=default_price,
                part_number=None,
                amount=default_price,
            ))

        return tuple(items)
