import os
import uuid
import shutil
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from src.infrastructure.vision_llm_extractor import VisionLlmQuotationExtractor, ExtractedQuotationSchema, ExtractedItemSchema
from src.application.quotation_service import QuotationApplicationService
from src.domain.quotation import Quotation


class StagedItem(BaseModel):
    item_number: int = 1
    part_number: Optional[str] = None
    description: str
    quantity: float = 1.0
    unit: str = "Pcs"
    unit_price: float = 0.0
    total_price: Optional[float] = None
    confidence: float = 0.95
    is_user_modified: bool = False


class StagedQuotationDraft(BaseModel):
    staging_id: str = Field(default_factory=lambda: f"STAGE-{uuid.uuid4().hex[:8].upper()}")
    uploaded_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    filename: str
    file_path: str
    pdf_sha256: str
    quotation_number: str
    vendor_name: str
    vendor_tax_id: Optional[str] = None
    issue_date: str
    expiration_date: str
    currency: str = "THB"
    total_amount: float = 0.0
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    items: List[StagedItem] = Field(default_factory=list)
    extraction_source: str = "VISION_LLM"
    status: str = "PENDING_VERIFICATION"  # 'PENDING_VERIFICATION', 'VERIFIED_COMMITTED', 'DISCARDED'
    validation_warnings: List[str] = Field(default_factory=list)
    raw_text: str = ""


class HitlVerificationService:
    """Human-in-the-Loop (HITL) procurement verification workflow service.

    Allows procurement teams to stage, review, modify, and audit quotation drafts before database persistence.
    """

    def __init__(self, quotation_service: QuotationApplicationService, staging_dir: str = "storage/staging") -> None:
        self.quotation_service = quotation_service
        self.staging_dir = staging_dir
        self.extractor = VisionLlmQuotationExtractor()
        self._staged_drafts: Dict[str, StagedQuotationDraft] = {}
        os.makedirs(staging_dir, exist_ok=True)

    def stage_pdf_quotation(self, temp_file_path: str, filename: str) -> StagedQuotationDraft:
        """Ingests PDF through Vision-LLM and stages as an uncommitted draft for HITL validation."""
        os.makedirs(self.staging_dir, exist_ok=True)
        staging_id = f"STAGE-{uuid.uuid4().hex[:8].upper()}"
        staged_file_path = os.path.join(self.staging_dir, f"{staging_id}_{filename}")
        shutil.copyfile(temp_file_path, staged_file_path)

        # Run automated Vision-LLM extraction
        extracted_schema = self.extractor.extract_from_pdf(staged_file_path)

        # Check validation warnings
        warnings = []
        try:
            iss = date.fromisoformat(extracted_schema.issue_date)
            exp = date.fromisoformat(extracted_schema.expiration_date)
            if exp <= iss:
                warnings.append("Expiration date is before or equal to Issue date")
            if exp < date.today():
                warnings.append("Quotation has already expired based on current calendar date")
        except Exception:
            warnings.append("Invalid date format detected")

        if not extracted_schema.items:
            warnings.append("No line items extracted from document table")
        if not extracted_schema.vendor_tax_id:
            warnings.append("Vendor Tax ID was not detected in document")

        staged_items = [
            StagedItem(
                item_number=it.item_number,
                part_number=it.part_number,
                description=it.description,
                quantity=it.quantity,
                unit=it.unit,
                unit_price=it.unit_price,
                total_price=it.total_price or (it.quantity * it.unit_price),
                confidence=it.confidence,
                is_user_modified=False,
            )
            for it in extracted_schema.items
        ]

        staged = StagedQuotationDraft(
            staging_id=staging_id,
            filename=filename,
            file_path=staged_file_path,
            pdf_sha256=extracted_schema.sha256,
            quotation_number=extracted_schema.quotation_number,
            vendor_name=extracted_schema.vendor_name,
            vendor_tax_id=extracted_schema.vendor_tax_id,
            issue_date=extracted_schema.issue_date,
            expiration_date=extracted_schema.expiration_date,
            currency=extracted_schema.currency,
            total_amount=extracted_schema.total_amount,
            payment_terms=extracted_schema.payment_terms,
            delivery_terms=extracted_schema.delivery_terms,
            items=staged_items,
            extraction_source=extracted_schema.extraction_source,
            status="PENDING_VERIFICATION",
            validation_warnings=warnings,
            raw_text=extracted_schema.raw_text,
        )

        self._staged_drafts[staging_id] = staged
        return staged

    def get_staged_draft(self, staging_id: str) -> Optional[StagedQuotationDraft]:
        return self._staged_drafts.get(staging_id)

    def list_pending_drafts(self) -> List[StagedQuotationDraft]:
        return [d for d in self._staged_drafts.values() if d.status == "PENDING_VERIFICATION"]

    def update_draft(self, staging_id: str, updates: Dict[str, Any]) -> StagedQuotationDraft:
        """Applies manual human edits to staged quotation draft."""
        draft = self._staged_drafts.get(staging_id)
        if not draft:
            raise KeyError(f"Staged draft {staging_id} not found")

        if "quotation_number" in updates:
            draft.quotation_number = updates["quotation_number"].strip()
        if "vendor_name" in updates:
            draft.vendor_name = updates["vendor_name"].strip()
        if "vendor_tax_id" in updates:
            draft.vendor_tax_id = updates["vendor_tax_id"].strip() if updates["vendor_tax_id"] else None
        if "issue_date" in updates:
            draft.issue_date = updates["issue_date"].strip()
        if "expiration_date" in updates:
            draft.expiration_date = updates["expiration_date"].strip()
        if "currency" in updates:
            draft.currency = updates["currency"].strip()

        if "items" in updates and isinstance(updates["items"], list):
            new_items = []
            for idx, it in enumerate(updates["items"]):
                new_items.append(
                    StagedItem(
                        item_number=it.get("item_number", idx + 1),
                        part_number=it.get("part_number"),
                        description=it.get("description", "").strip(),
                        quantity=float(it.get("quantity", 1.0)),
                        unit=it.get("unit", "Pcs") or "Pcs",
                        unit_price=float(it.get("unit_price", 0.0)),
                        total_price=float(it.get("quantity", 1.0)) * float(it.get("unit_price", 0.0)),
                        confidence=1.0,  # Human verified
                        is_user_modified=True,
                    )
                )
            draft.items = new_items
            draft.total_amount = sum(it.total_price or 0.0 for it in new_items)

        # Re-run validation
        warnings = []
        try:
            iss = date.fromisoformat(draft.issue_date)
            exp = date.fromisoformat(draft.expiration_date)
            if exp <= iss:
                warnings.append("Expiration date is before or equal to Issue date")
        except Exception:
            warnings.append("Invalid date format")

        draft.validation_warnings = warnings
        return draft

    def commit_draft_to_database(self, staging_id: str, user_role: str = "PH_USER") -> Quotation:
        """Validates human review and commits staged draft to permanent database and indices."""
        draft = self._staged_drafts.get(staging_id)
        if not draft:
            raise KeyError(f"Staged draft {staging_id} not found")
        if draft.status == "VERIFIED_COMMITTED":
            raise ValueError(f"Draft {staging_id} is already committed")

        # Persist PDF file to permanent storage
        permanent_pdf_dir = "storage/pdf"
        os.makedirs(permanent_pdf_dir, exist_ok=True)
        final_pdf_path = os.path.join(permanent_pdf_dir, draft.filename)
        if draft.file_path != final_pdf_path and os.path.exists(draft.file_path):
            shutil.copyfile(draft.file_path, final_pdf_path)

        iss_date = date.fromisoformat(draft.issue_date)
        exp_date = date.fromisoformat(draft.expiration_date)

        items_dict = [
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

        committed_quotation = self.quotation_service.register_quotation(
            quotation_number=draft.quotation_number,
            vendor_name=draft.vendor_name,
            issue_date=iss_date,
            expiration_date=exp_date,
            items=items_dict,
            pdf_path=final_pdf_path,
            pdf_sha256=draft.pdf_sha256,
            user_role=user_role,
            currency=draft.currency,
            vendor_tax_id=draft.vendor_tax_id,
            raw_text=draft.raw_text,
        )

        draft.status = "VERIFIED_COMMITTED"
        return committed_quotation

    def discard_draft(self, staging_id: str) -> None:
        draft = self._staged_drafts.pop(staging_id, None)
        if draft and os.path.exists(draft.file_path):
            try:
                os.remove(draft.file_path)
            except Exception:
                pass
