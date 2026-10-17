from datetime import date, datetime, timezone
import sqlite3
from typing import Optional

from src.domain.manual_quotation_request import (
    ManualQuotationRequest,
    RequestStatus,
    RequestUrgency,
)
from src.domain.quotation import QuotationId


class SqliteManualRequestRepository:
    """SQLite-backed persistence for ManualQuotationRequest aggregate root."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    def initialize_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_quotation_requests (
                ticket_id TEXT PRIMARY KEY,
                requester_user_id TEXT NOT NULL,
                department TEXT NOT NULL,
                item_description TEXT NOT NULL,
                part_number TEXT,
                target_quantity REAL,
                target_unit TEXT,
                needed_by_date TEXT,
                urgency TEXT NOT NULL,
                status TEXT NOT NULL,
                fulfilled_quotation_id TEXT,
                assigned_ph_user_id TEXT,
                rejection_reason TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def save(self, request: ManualQuotationRequest) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO manual_quotation_requests (
                ticket_id, requester_user_id, department, item_description, part_number,
                target_quantity, target_unit, needed_by_date, urgency, status,
                fulfilled_quotation_id, assigned_ph_user_id, rejection_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                requester_user_id = excluded.requester_user_id,
                department = excluded.department,
                item_description = excluded.item_description,
                part_number = excluded.part_number,
                target_quantity = excluded.target_quantity,
                target_unit = excluded.target_unit,
                needed_by_date = excluded.needed_by_date,
                urgency = excluded.urgency,
                status = excluded.status,
                fulfilled_quotation_id = excluded.fulfilled_quotation_id,
                assigned_ph_user_id = excluded.assigned_ph_user_id,
                rejection_reason = excluded.rejection_reason
        """, (
            request.ticket_id,
            request.requester_user_id,
            request.department,
            request.item_description,
            request.part_number,
            request.target_quantity,
            request.target_unit,
            request.needed_by_date.isoformat() if request.needed_by_date else None,
            request.urgency.value,
            request.status.value,
            str(request.fulfilled_quotation_id) if request.fulfilled_quotation_id else None,
            request.assigned_ph_user_id,
            request.rejection_reason,
            request.created_at.isoformat(),
        ))
        self._conn.commit()

    def find_by_ticket_id(self, ticket_id: str) -> Optional[ManualQuotationRequest]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM manual_quotation_requests WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._map_row_to_request(row)

    def find_all(self) -> list[ManualQuotationRequest]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM manual_quotation_requests ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [self._map_row_to_request(r) for r in rows]

    def find_by_status(self, status: RequestStatus) -> list[ManualQuotationRequest]:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM manual_quotation_requests WHERE status = ? ORDER BY created_at DESC",
            (status.value,)
        )
        rows = cursor.fetchall()
        return [self._map_row_to_request(r) for r in rows]

    def _map_row_to_request(self, row: sqlite3.Row) -> ManualQuotationRequest:
        needed_by = date.fromisoformat(row["needed_by_date"]) if row["needed_by_date"] else None
        fulfilled_id = QuotationId(row["fulfilled_quotation_id"]) if row["fulfilled_quotation_id"] else None

        return ManualQuotationRequest(
            ticket_id=row["ticket_id"],
            requester_user_id=row["requester_user_id"],
            department=row["department"],
            item_description=row["item_description"],
            part_number=row["part_number"],
            target_quantity=row["target_quantity"],
            target_unit=row["target_unit"],
            needed_by_date=needed_by,
            urgency=RequestUrgency(row["urgency"]),
            status=RequestStatus(row["status"]),
            fulfilled_quotation_id=fulfilled_id,
            assigned_ph_user_id=row["assigned_ph_user_id"],
            rejection_reason=row["rejection_reason"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
