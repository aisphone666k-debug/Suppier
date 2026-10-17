import re
from typing import Set


class MultilingualLexicon:
    """Domain lexicon establishing semantic equivalence across English, Thai, and Japanese manufacturing terms."""

    # Clusters of semantically equivalent terms: (English, Thai, Japanese)
    _CLUSTERS = [
        # Box / Enclosure / Container / Receptacle
        {
            "box", "boxes", "botton box", "button box", "control box", "enclosure", "container", "receptacle", "casing", "housing", "cabinet",
            "กล่อง", "กล่องควบคุม", "กล่องสวิตช์", "ตู้ควบคุม", "ภาชนะ", "ที่ใส่", "ที่บรรจุ", "กล่องบรรจุ", "หีบ", "ตู้",
            "箱", "ボックス", "コントロールボックス", "ケース", "筐体", "容器", "キャビネット",
        },
        # Belt / Transmission
        {
            "belt", "belts", "v-belt", "v belt", "transmission belt", "rubber belt", "transmission", "drive belt",
            "สายพาน", "สายพานส่งกำลัง", "สายพานร่องวี", "สายพานยาง", "อุปกรณ์ส่งกำลัง",
            "ベルト", "Vベルト", "伝動ベルト", "ゴムベルト", "伝動装置",
        },
        # Quotation / Proposal
        {
            "quotation", "quote", "price quote", "estimate",
            "ใบเสนอราคา", "ราคากลาง", "ราคาเสนอ",
            "見積", "見積書", "御見積書", "見積り",
        },
        # Bearing
        {
            "bearing", "bearings", "ball bearing",
            "ตลับลูกปืน", "ลูกปืน",
            "ベアリング", "軸受", "玉軸受",
        },
        # Valve
        {
            "valve", "valves", "solenoid valve",
            "วาล์ว", "โซลินอยด์วาล์ว", "วาล์วควบคุม",
            "バルブ", "弁", "電磁弁",
        },
        # Cylinder
        {
            "cylinder", "cylinders", "air cylinder", "pneumatic cylinder",
            "กระบอกสูบ", "กระบอกลม",
            "シリンダ", "シリンダー", "エアシリンダ", "気筒",
        },
        # Motor
        {
            "motor", "motors", "servo motor",
            "มอเตอร์", "เซอร์โวมอเตอร์",
            "モーター", "電動機", "サーボモータ", "サーボモーター",
        },
        # Sensor
        {
            "sensor", "sensors", "proximity sensor",
            "เซนเซอร์", "พร็อกซิมิตี้เซนเซอร์",
            "センサー", "センサ", "近接センサ",
        },
        # Switch
        {
            "switch", "switches", "button switch",
            "สวิตช์", "สวิทช์", "ปุ่มกด",
            "スイッチ", "押しボタンスイッチ",
        },
        # Flange
        {
            "flange", "flanges",
            "หน้าแปลน", "แปลน",
            "フランジ",
        },
        # Cable / Wire
        {
            "cable", "cables", "wire", "wires",
            "สายไฟ", "สายเคเบิล",
            "ケーブル", "電線", "ワイヤー",
        },
    ]

    def __init__(self) -> None:
        self._lookup: dict[str, Set[str]] = {}
        for cluster in self._CLUSTERS:
            for term in cluster:
                normalized = self._normalize(term)
                if normalized not in self._lookup:
                    self._lookup[normalized] = set()
                self._lookup[normalized].update(cluster)

    def _normalize(self, text: str) -> str:
        return text.strip().lower()

    def expand_terms(self, term: str) -> Set[str]:
        """Returns all cross-lingual equivalents (Thai, Japanese, English) for a given term."""
        normalized = self._normalize(term)
        results: Set[str] = {normalized}

        # Direct match
        if normalized in self._lookup:
            results.update(self._lookup[normalized])

        # Compound / phrase match where key is contained in normalized
        for key, synonyms in self._lookup.items():
            if not key.isascii():
                # Thai or Japanese characters (e.g. 箱, ボックス, กล่อง)
                if key in normalized:
                    results.update(synonyms)
            elif len(key) >= 3:
                # English words / phrases (e.g. box, belt, button box)
                pattern = r"(?:\b|_)" + re.escape(key) + r"(?:\b|_)"
                if re.search(pattern, normalized):
                    results.update(synonyms)

        return results

    def extract_unicode_tokens(self, text: str) -> list[str]:
        """Extracts words from text supporting English, Thai (U+0E00-U+0E7F), and Japanese (Kanji/Kana)."""
        # Match sequences of alphanumeric or Thai/Japanese characters
        pattern = r"[A-Za-z0-9_\-]+|[\u0E00-\u0E7F]+|[\u4E00-\u9FFF]+|[\u3040-\u309F]+|[\u30A0-\u30FF]+"
        tokens = re.findall(pattern, text)
        result: list[str] = []
        for t in tokens:
            cleaned = t.strip().lower()
            if len(cleaned) >= 1:
                result.append(cleaned)
        return result
