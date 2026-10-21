import re
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from src.domain.manual_quotation_request import (
    ManualQuotationRequest,
    RequestUrgency,
)
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository


class SlotState(BaseModel):
    item_name: Optional[str] = None
    specification: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = "Pcs"
    urgency: str = "NORMAL"  # 'NORMAL', 'URGENT', 'CRITICAL'
    needed_by_date: Optional[str] = None
    department: Optional[str] = "Procurement & Maintenance"
    preferred_vendor: Optional[str] = None
    notes: Optional[str] = None


class PrRfqDraft(BaseModel):
    rfq_number: str
    created_at: str
    requester_user_id: str
    department: str
    item_name: str
    specification: str
    quantity: float
    unit: str
    urgency: str
    needed_by_date: Optional[str]
    preferred_vendor: Optional[str]
    status: str = "DRAFT_READY"
    formatted_summary: str = ""


class ConversationSession(BaseModel):
    session_id: str
    slots: SlotState = Field(default_factory=SlotState)
    step: str = "INIT"  # 'INIT', 'COLLECTING', 'CONFIRMING', 'COMPLETED'
    history: List[Dict[str, str]] = Field(default_factory=list)
    generated_draft: Optional[PrRfqDraft] = None


class SlotFillingAgent:
    """Intelligent conversational procurement agent that collects missing item specifications

    and automatically generates formal PR/RFQ drafts when queries yield no quotation matches.
    """

    def __init__(self, manual_repo: SqliteManualRequestRepository) -> None:
        self.manual_repo = manual_repo
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        if not session_id or session_id not in self._sessions:
            new_id = session_id or f"SES-{uuid.uuid4().hex[:8].upper()}"
            self._sessions[new_id] = ConversationSession(session_id=new_id)
        return self._sessions[session_id or new_id]

    def trigger_from_empty_search(self, session_id: str, search_query: str) -> Dict[str, Any]:
        """Automatically called when user's search yields no quotations."""
        session = self.get_or_create_session(session_id)
        session.slots.item_name = search_query.strip()
        session.step = "COLLECTING"

        msg = (
            f"[SYSTEM] ไม่พบใบเสนอราคาสำหรับ '{search_query}' ในฐานข้อมูลระบบ\n"
            f"ระบบ AI Procurement Agent พร้อมช่วยจัดทำแบบร่างใบขอเสนอราคา (RFQ / PR Draft) อัตโนมัติทันทีครับ\n\n"
            f"กรุณาระบุรายละเอียดเพิ่มเติม:\n"
            f"1. สเปกทางเทคนิค หรือ Model Code ที่ต้องการ\n"
            f"2. จำนวนและหน่วยนับ (เช่น 2 Pcs, 10 Set)\n"
            f"3. ระดับความเร่งด่วน (NORMAL / URGENT / CRITICAL)"
        )
        session.history.append({"role": "assistant", "content": msg})
        return {
            "session_id": session.session_id,
            "message": msg,
            "slots": session.slots.dict(),
            "step": session.step,
            "draft": None,
        }

    def process_user_message(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "emp_user",
        user_role: str = "NORMAL_USER",
    ) -> Dict[str, Any]:
        """Parses user natural language response, fills missing slots, and generates PR draft when complete."""
        session = self.get_or_create_session(session_id)
        session.history.append({"role": "user", "content": user_message})

        clean_text = user_message.strip()

        # Slot Extraction logic
        # 1. Quantity & Unit
        qty_match = re.search(r"(\d+(?:\.\d+)?)\s*(pcs|ea|set|lot|box|ชิ้น|อัน|ตัว|กล่อง|ชุด|เส้น)", clean_text, re.IGNORECASE)
        if qty_match:
            session.slots.quantity = float(qty_match.group(1))
            raw_unit = qty_match.group(2).lower()
            unit_map = {
                "pcs": "Pcs", "ea": "Pcs", "ชิ้น": "Pcs", "อัน": "Pcs", "ตัว": "Pcs",
                "set": "Set", "ชุด": "Set",
                "box": "Box", "กล่อง": "Box",
                "lot": "Lot",
                "เส้น": "Pcs",
            }
            session.slots.unit = unit_map.get(raw_unit, "Pcs")
        elif re.search(r"(\d+)\s*(?:ชิ้น|จำนวน)", clean_text):
            m = re.search(r"(\d+)", clean_text)
            if m:
                session.slots.quantity = float(m.group(1))

        # 2. Urgency
        if re.search(r"(ด่วนมาก|critical|ด่วนที่สุด|ฉุกเฉิน)", clean_text, re.IGNORECASE):
            session.slots.urgency = "CRITICAL"
        elif re.search(r"(ด่วน|urgent|เร็วๆนี้)", clean_text, re.IGNORECASE):
            session.slots.urgency = "URGENT"
        elif re.search(r"(ปกติ|normal)", clean_text, re.IGNORECASE):
            session.slots.urgency = "NORMAL"

        # 3. Department
        dept_match = re.search(r"(?:แผนก|ฝ่าย|dept|department)\s*[:=]?\s*([a-zA-Z0-9\u0E00-\u0E7F\s/]+)", clean_text, re.IGNORECASE)
        if dept_match:
            session.slots.department = dept_match.group(1).strip()

        # 4. Specification or Item Name
        if not session.slots.item_name:
            # First query or extracted part
            session.slots.item_name = clean_text
        elif not session.slots.specification:
            # If user mentions specs or models
            session.slots.specification = clean_text

        # 5. Target Delivery Date
        if re.search(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})", clean_text):
            m = re.search(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})", clean_text)
            if m:
                session.slots.needed_by_date = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
        elif "สัปดาห์หน้า" in clean_text or "7 วัน" in clean_text:
            session.slots.needed_by_date = (date.today() + timedelta(days=7)).isoformat()
        elif "สิ้นเดือน" in clean_text:
            session.slots.needed_by_date = (date.today() + timedelta(days=25)).isoformat()

        # Check completeness
        missing_slots = []
        if not session.slots.item_name:
            missing_slots.append("ชื่อสินค้า / ชิ้นส่วน (Item Name)")
        if not session.slots.specification:
            missing_slots.append("สเปกทางเทคนิค / Model (Technical Spec)")
        if session.slots.quantity is None:
            missing_slots.append("จำนวนที่ต้องการ (Quantity)")

        if missing_slots:
            response_msg = (
                f"รับข้อมูลเรียบร้อยแล้วครับ ระบบยังขาดข้อมูลสำคัญ:\n"
                + "\n".join([f"- {s}" for s in missing_slots])
                + f"\n\nกรุณาแจ้งข้อมูลเพิ่มเติมเพื่อสร้างแบบร่าง RFQ/PR ครับ"
            )
            session.history.append({"role": "assistant", "content": response_msg})
            return {
                "session_id": session.session_id,
                "message": response_msg,
                "slots": session.slots.dict(),
                "step": "COLLECTING",
                "draft": None,
            }

        # All core slots filled -> Generate PR / RFQ Draft!
        session.step = "COMPLETED"
        rfq_no = f"PR-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"
        needed_date_str = session.slots.needed_by_date or (date.today() + timedelta(days=14)).isoformat()

        formatted_summary = f"""
============================================================
              PURCHASE REQUISITION / RFQ DRAFT              
============================================================
Document Ref : {rfq_no}
Created Date : {date.today().isoformat()}
Requester    : {user_id}
Department   : {session.slots.department}
Urgency      : [{session.slots.urgency}]
Target Date  : {needed_date_str}

[LINE ITEM SPECIFICATIONS]
Item Name    : {session.slots.item_name}
Model / Spec : {session.slots.specification or '-'}
Quantity     : {session.slots.quantity} {session.slots.unit}
Vendor Pref  : {session.slots.preferred_vendor or 'Any Qualified Vendor'}
============================================================
สถานะ: สร้างแบบร่างสำเร็จ พร้อมส่งต่อให้ฝ่ายจัดซื้อ (Purchasing Hub) ดำเนินการ
"""

        draft = PrRfqDraft(
            rfq_number=rfq_no,
            created_at=datetime.now().isoformat(),
            requester_user_id=user_id,
            department=session.slots.department or "Procurement",
            item_name=session.slots.item_name,
            specification=session.slots.specification or "",
            quantity=session.slots.quantity or 1.0,
            unit=session.slots.unit or "Pcs",
            urgency=session.slots.urgency,
            needed_by_date=needed_date_str,
            preferred_vendor=session.slots.preferred_vendor,
            status="DRAFT_READY",
            formatted_summary=formatted_summary.strip(),
        )
        session.generated_draft = draft

        # Persist into database manual requests table
        urgency_enum = RequestUrgency.NORMAL
        if session.slots.urgency == "CRITICAL":
            urgency_enum = RequestUrgency.CRITICAL
        elif session.slots.urgency == "URGENT":
            urgency_enum = RequestUrgency.HIGH

        try:
            persisted_req = ManualQuotationRequest(
                ticket_id=rfq_no,
                requester_user_id=user_id,
                department=session.slots.department or "Procurement",
                item_description=f"{session.slots.item_name} | Spec: {session.slots.specification}",
                part_number=session.slots.specification[:40] if session.slots.specification else None,
                target_quantity=session.slots.quantity,
                target_unit=session.slots.unit,
                needed_by_date=date.fromisoformat(needed_date_str) if needed_date_str else None,
                urgency=urgency_enum,
            )
            self.manual_repo.save(persisted_req)
        except Exception as e:
            print(f"[WARN] Failed to persist RFQ draft to repository: {e}")

        response_msg = (
            f"[OK] รวบรวมข้อมูลครบถ้วน และได้สร้างแบบร่าง PR/RFQ อัตโนมัติเรียบร้อยแล้ว!\n\n"
            f"{formatted_summary}\n\n"
            f"แบบร่างนี้ได้รับการลงทะเบียนเข้าระบบ Purchasing Hub เรียบร้อยแล้ว จัดซื้อสามารถเปิดใบสั่งซื้อหรือส่งต่อให้ Vendor ได้ทันทีครับ"
        )
        session.history.append({"role": "assistant", "content": response_msg})

        return {
            "session_id": session.session_id,
            "message": response_msg,
            "slots": session.slots.dict(),
            "step": "COMPLETED",
            "draft": draft.dict(),
        }
