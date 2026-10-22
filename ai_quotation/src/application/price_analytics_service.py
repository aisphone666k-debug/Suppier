import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PricePoint(BaseModel):
    date: str
    quotation_number: str
    vendor_name: str
    unit_price: float
    currency: str = "THB"
    quantity: float = 1.0


class PriceTrendAnalysis(BaseModel):
    query_term: str
    matched_part_number: Optional[str]
    matched_description: str
    data_points: List[PricePoint]
    min_price: float
    max_price: float
    avg_price: float
    latest_price: float
    price_change_pct: float
    trend_direction: str  # 'UP', 'DOWN', 'STABLE'
    recommendation: str


class SystemAlert(BaseModel):
    alert_id: str
    alert_type: str  # 'PRICE_INCREASE', 'PRICE_DROP', 'EXPIRING_SOON', 'RFQ_GENERATED'
    title: str
    message: str
    severity: str  # 'INFO', 'WARNING', 'CRITICAL'
    created_at: str
    related_quotation_id: Optional[str] = None
    is_read: bool = False


class PriceAnalyticsService:
    """Historical price analytics and automated notification alert system for procurement intelligence."""

    def __init__(self, db_conn: sqlite3.Connection) -> None:
        self.conn = db_conn
        self._alerts: List[SystemAlert] = []
        self._init_alert_table()

    def _init_alert_table(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_alerts (
                alert_id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                created_at TEXT NOT NULL,
                related_quotation_id TEXT,
                is_read INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def add_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        severity: str = "INFO",
        related_quotation_id: Optional[str] = None,
    ) -> SystemAlert:
        import uuid
        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        now_str = datetime.now().isoformat()
        alert = SystemAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            title=title,
            message=message,
            severity=severity,
            created_at=now_str,
            related_quotation_id=related_quotation_id,
            is_read=False,
        )
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO system_alerts 
            (alert_id, alert_type, title, message, severity, created_at, related_quotation_id, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (alert_id, alert_type, title, message, severity, now_str, related_quotation_id, 0),
        )
        self.conn.commit()
        return alert

    def get_recent_alerts(self, limit: int = 15) -> List[SystemAlert]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT alert_id, alert_type, title, message, severity, created_at, related_quotation_id, is_read
            FROM system_alerts
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            SystemAlert(
                alert_id=r[0],
                alert_type=r[1],
                title=r[2],
                message=r[3],
                severity=r[4],
                created_at=r[5],
                related_quotation_id=r[6],
                is_read=bool(r[7]),
            )
            for r in rows
        ]

    def analyze_price_trends(self, query: str) -> Optional[PriceTrendAnalysis]:
        """Analyzes historical prices for part numbers or descriptions matching query."""
        cur = self.conn.cursor()
        q_clean = query.strip()
        like_pattern = f"%{q_clean}%"

        cur.execute(
            """
            SELECT q.issue_date, q.quotation_number, q.vendor_name, q.currency,
                   qi.part_number, qi.description, qi.unit_price, qi.quantity
            FROM quotation_items qi
            JOIN quotations q ON qi.quotation_id = q.id
            WHERE qi.part_number LIKE ? OR qi.description LIKE ? OR q.vendor_name LIKE ?
            ORDER BY q.issue_date ASC
            """,
            (like_pattern, like_pattern, like_pattern),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        points: List[PricePoint] = []
        prices: List[float] = []
        matched_pn = rows[0][4]
        matched_desc = rows[0][5]

        for r in rows:
            iss_date, q_num, v_name, curr, pn, desc, u_price, qty = r
            if u_price is not None and u_price > 0:
                points.append(
                    PricePoint(
                        date=iss_date or date.today().isoformat(),
                        quotation_number=q_num,
                        vendor_name=v_name,
                        unit_price=float(u_price),
                        currency=curr or "THB",
                        quantity=float(qty or 1.0),
                    )
                )
                prices.append(float(u_price))

        if not prices:
            return None

        min_p = min(prices)
        max_p = max(prices)
        avg_p = sum(prices) / len(prices)
        latest_p = prices[-1]

        # Trend calculation
        if len(prices) >= 2:
            first_p = prices[0]
            change_pct = round(((latest_p - first_p) / (first_p + 1e-5)) * 100, 2)
        else:
            change_pct = 0.0

        if change_pct > 3.0:
            trend = "UP"
            rec = f"ราคาปรับตัวขึ้น {change_pct}% ควรเจรจาต่อรอง หรือสอบเทียบราคาจาก Vendor ทางเลือก"
        elif change_pct < -3.0:
            trend = "DOWN"
            rec = f"ราคาลดลง {abs(change_pct)}% เป็นราคาที่ดีในการจัดซื้อสต็อกสำรอง"
        else:
            trend = "STABLE"
            rec = "ราคาค่อนข้างคงที่ตามเกณฑ์มาตรฐานตลาด"

        return PriceTrendAnalysis(
            query_term=q_clean,
            matched_part_number=matched_pn,
            matched_description=matched_desc,
            data_points=points,
            min_price=min_p,
            max_price=max_p,
            avg_price=round(avg_p, 2),
            latest_price=latest_p,
            price_change_pct=change_pct,
            trend_direction=trend,
            recommendation=rec,
        )

    def scan_and_generate_expiration_alerts(self, days_threshold: int = 30) -> int:
        """Scans active quotations and issues automated alerts for those nearing expiration."""
        today = date.today()
        target_date = today + timedelta(days=days_threshold)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, quotation_number, vendor_name, expiration_date
            FROM quotations
            WHERE status = 'ACTIVE' AND expiration_date <= ? AND expiration_date >= ?
            """,
            (target_date.isoformat(), today.isoformat()),
        )

        rows = cur.fetchall()
        alerts_created = 0
        for qid, q_num, v_name, exp in rows:
            # Check if alert already exists for this quotation
            cur.execute(
                "SELECT COUNT(*) FROM system_alerts WHERE related_quotation_id = ? AND alert_type = 'EXPIRING_SOON'",
                (qid,),
            )
            if cur.fetchone()[0] == 0:
                self.add_alert(
                    alert_type="EXPIRING_SOON",
                    title=f"Quotation {q_num} ใกล้หมดอายุ",
                    message=f"ใบเสนอราคาจาก {v_name} จะหมดอายุในวันที่ {exp} กรุณาดำเนินการต่ออายุ (Renewal)",
                    severity="WARNING",
                    related_quotation_id=qid,
                )
                alerts_created += 1
        return alerts_created
