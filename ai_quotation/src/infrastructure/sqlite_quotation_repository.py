import sqlite3
from datetime import date
from typing import Optional

from src.domain.quotation import (
    Quotation,
    QuotationId,
    QuotationStatus,
    QuotationItem,
    QuotationAcknowledgment,
)
from src.domain.validity_period import ValidityPeriod


class SqliteQuotationRepository:
    """SQLite-backed persistence for Quotation aggregate root."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    def initialize_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotations (
                id TEXT PRIMARY KEY,
                quotation_number TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                vendor_tax_id TEXT,
                issue_date TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'THB',
                status TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                pdf_sha256 TEXT NOT NULL,
                raw_text TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id TEXT NOT NULL,
                item_number INTEGER NOT NULL,
                part_number TEXT,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                unit_price REAL NOT NULL,
                drawing_number TEXT,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
            )
        """)
        try:
            cursor.execute("ALTER TABLE quotation_items ADD COLUMN drawing_number TEXT")
        except sqlite3.OperationalError:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotation_acknowledgments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                received_date TEXT NOT NULL,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id)
            )
        """)
        self._conn.commit()

    def save(self, quotation: Quotation) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO quotations (
                id, quotation_number, vendor_name, vendor_tax_id, issue_date, expiration_date,
                currency, status, pdf_path, pdf_sha256, raw_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                quotation_number = excluded.quotation_number,
                vendor_name = excluded.vendor_name,
                vendor_tax_id = excluded.vendor_tax_id,
                issue_date = excluded.issue_date,
                expiration_date = excluded.expiration_date,
                currency = excluded.currency,
                status = excluded.status,
                pdf_path = excluded.pdf_path,
                pdf_sha256 = excluded.pdf_sha256,
                raw_text = excluded.raw_text
        """, (
            str(quotation.quotation_id),
            quotation.quotation_number,
            quotation.vendor_name,
            quotation.vendor_tax_id,
            quotation.validity_period.issue_date.isoformat(),
            quotation.validity_period.expiration_date.isoformat(),
            quotation.currency,
            quotation.status.value,
            quotation.pdf_path,
            quotation.pdf_sha256,
            quotation.raw_text,
        ))

        # Replace items
        cursor.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (str(quotation.quotation_id),))
        for item in quotation.items:
            cursor.execute("""
                INSERT INTO quotation_items (
                    quotation_id, item_number, part_number, description, quantity, unit, unit_price, drawing_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(quotation.quotation_id),
                item.item_number,
                item.part_number,
                item.description,
                item.quantity,
                item.unit,
                item.unit_price,
                getattr(item, "drawing_number", None),
            ))
        self._conn.commit()

    def find_by_id(self, quotation_id: QuotationId) -> Optional[Quotation]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM quotations WHERE id = ?", (str(quotation_id),))
        row = cursor.fetchone()
        if not row:
            return None
        return self._map_row_to_quotation(row)

    def find_all(self) -> list[Quotation]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM quotations")
        rows = cursor.fetchall()
        return [self._map_row_to_quotation(r) for r in rows]

    def find_expired(self, reference_date: date) -> list[Quotation]:
        all_quotations = self.find_all()
        expired = []
        for q in all_quotations:
            q.evaluate_expiration(reference_date)
            if q.status == QuotationStatus.EXPIRED:
                expired.append(q)
        return expired

    def find_active(self, reference_date: date) -> list[Quotation]:
        all_quotations = self.find_all()
        active = []
        for q in all_quotations:
            q.evaluate_expiration(reference_date)
            if q.status == QuotationStatus.ACTIVE:
                active.append(q)
        return active

    def record_acknowledgment(self, acknowledgment: QuotationAcknowledgment) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO quotation_acknowledgments (quotation_id, user_id, received_date)
            VALUES (?, ?, ?)
        """, (
            str(acknowledgment.quotation_id),
            acknowledgment.user_id,
            acknowledgment.received_date.isoformat(),
        ))
        self._conn.commit()

    def get_acknowledgments(self, quotation_id: QuotationId) -> list[QuotationAcknowledgment]:
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM quotation_acknowledgments WHERE quotation_id = ?
        """, (str(quotation_id),))
        rows = cursor.fetchall()
        return [
            QuotationAcknowledgment(
                quotation_id=QuotationId(r["quotation_id"]),
                user_id=r["user_id"],
                received_date=date.fromisoformat(r["received_date"]),
            )
            for r in rows
        ]

    def _map_row_to_quotation(self, row: sqlite3.Row) -> Quotation:
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM quotation_items WHERE quotation_id = ? ORDER BY item_number ASC
        """, (row["id"],))
        item_rows = cursor.fetchall()

        items = tuple(
            QuotationItem(
                item_number=ir["item_number"],
                description=ir["description"],
                quantity=ir["quantity"],
                unit=ir["unit"],
                unit_price=ir["unit_price"],
                part_number=ir["part_number"],
                drawing_number=ir["drawing_number"] if "drawing_number" in ir.keys() else None,
            )
            for ir in item_rows
        )

        return Quotation(
            quotation_id=QuotationId(row["id"]),
            quotation_number=row["quotation_number"],
            vendor_name=row["vendor_name"],
            vendor_tax_id=row["vendor_tax_id"],
            validity_period=ValidityPeriod(
                issue_date=date.fromisoformat(row["issue_date"]),
                expiration_date=date.fromisoformat(row["expiration_date"]),
            ),
            status=QuotationStatus(row["status"]),
            items=items,
            pdf_path=row["pdf_path"],
            pdf_sha256=row["pdf_sha256"],
            currency=row["currency"],
            raw_text=row["raw_text"],
        )
