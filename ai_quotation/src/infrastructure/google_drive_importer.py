import os
import re
import urllib.parse
import uuid
import httpx
from typing import Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
}

class GoogleDriveImportError(Exception):
    pass

class GoogleDriveImporter:
    """
    Handles extracting Google Drive links, downloading PDF files or exporting
    Google Docs/Sheets as PDF, and scanning public folders.
    """

    @staticmethod
    def extract_gdrive_targets(text_or_url: str) -> list[dict]:
        """
        Extracts Google Drive file, doc, and folder IDs from URLs or dropped text/HTML.
        Returns list of dicts: {"type": "file"|"doc"|"sheet"|"folder", "id": str, "source": str}
        """
        results = []
        seen = set()

        if not text_or_url:
            return results

        # 1. Drive file links: drive.google.com/file/d/{id} or open?id={id} or uc?id={id}
        file_pattern = re.compile(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([a-zA-Z0-9_-]{20,})')
        for match in file_pattern.finditer(text_or_url):
            fid = match.group(1)
            if fid not in seen:
                seen.add(fid)
                results.append({"type": "file", "id": fid, "source": match.group(0)})

        # 2. Docs & Sheets links
        doc_pattern = re.compile(r'docs\.google\.com/document/d/([a-zA-Z0-9_-]{20,})')
        for match in doc_pattern.finditer(text_or_url):
            fid = match.group(1)
            if fid not in seen:
                seen.add(fid)
                results.append({"type": "doc", "id": fid, "source": match.group(0)})

        sheet_pattern = re.compile(r'docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]{20,})')
        for match in sheet_pattern.finditer(text_or_url):
            fid = match.group(1)
            if fid not in seen:
                seen.add(fid)
                results.append({"type": "sheet", "id": fid, "source": match.group(0)})

        # 3. Drive folder links: drive.google.com/drive/folders/{id} or /folders/{id}
        folder_pattern = re.compile(r'drive\.google\.com/(?:drive/(?:u/\d+/)?folders/|folders/)([a-zA-Z0-9_-]{20,})')
        for match in folder_pattern.finditer(text_or_url):
            fid = match.group(1)
            if fid not in seen:
                seen.add(fid)
                results.append({"type": "folder", "id": fid, "source": match.group(0)})

        # 4. Fallback: direct ID if user pasted just an ID string (25-50 alphanumeric characters)
        clean_str = text_or_url.strip()
        if re.fullmatch(r'[a-zA-Z0-9_-]{25,50}', clean_str) and clean_str not in seen:
            results.append({"type": "file", "id": clean_str, "source": clean_str})

        return results

    @staticmethod
    def fetch_folder_file_ids(folder_id: str) -> list[str]:
        """
        Attempts to list public file IDs from a Google Drive folder HTML response.
        Supports embedded JSON arrays, data attributes, escaped string IDs, and direct links.
        """
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        try:
            with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=25.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return []
                text = resp.text
                
                clean_ids = set()
                # 1. Embedded JSON table array pattern
                for m in re.finditer(r'\["([a-zA-Z0-9_-]{28,45})",\s*\[', text):
                    clean_ids.add(m.group(1))
                # 2. File / Doc / Sheet links inside folder page
                for m in re.finditer(r'(?:/file/d/|/document/d/|/spreadsheets/d/|uc\?id=)([a-zA-Z0-9_-]{25,50})', text):
                    clean_ids.add(m.group(1))
                # 3. HTML attributes like data-id or data-target
                for m in re.finditer(r'data-(?:id|target|item-id)=["\']([a-zA-Z0-9_-]{25,50})["\']', text):
                    clean_ids.add(m.group(1))
                # 4. JSON escaped IDs
                for m in re.finditer(r'\\\"([a-zA-Z0-9_-]{28,45})\\\"', text):
                    clean_ids.add(m.group(1))

                # Exclude the folder's own ID
                clean_ids.discard(folder_id)
                return list(clean_ids)
        except Exception:
            return []

    @classmethod
    def download_gdrive_pdf(
        cls,
        item_id: str,
        item_type: str = "file",
        dest_dir: str = "storage/staging"
    ) -> tuple[str, str]:
        """
        Downloads a Google Drive file or exports doc/sheet to PDF.
        Saves into dest_dir/stage_{prefix}_{filename}.
        Returns (temp_file_path, filename).
        Raises GoogleDriveImportError on failure.
        """
        os.makedirs(dest_dir, exist_ok=True)
        unique_prefix = uuid.uuid4().hex[:8]

        # Determine download candidates
        if item_type == "doc":
            candidate_urls = [
                f"https://docs.google.com/document/d/{item_id}/export?format=pdf",
                f"https://drive.usercontent.google.com/download?id={item_id}&export=download&confirm=t"
            ]
        elif item_type == "sheet":
            candidate_urls = [
                f"https://docs.google.com/spreadsheets/d/{item_id}/export?format=pdf",
                f"https://drive.usercontent.google.com/download?id={item_id}&export=download&confirm=t"
            ]
        else:
            candidate_urls = [
                f"https://drive.usercontent.google.com/download?id={item_id}&export=download&confirm=t",
                f"https://drive.google.com/uc?export=download&id={item_id}&confirm=t",
                f"https://docs.google.com/document/d/{item_id}/export?format=pdf",
                f"https://docs.google.com/spreadsheets/d/{item_id}/export?format=pdf"
            ]

        with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=45.0) as client:
            last_error = None
            for url in candidate_urls:
                try:
                    resp = client.get(url)
                    if resp.status_code == 403 or resp.status_code == 401 or "accounts.google.com" in str(resp.url):
                        raise GoogleDriveImportError(
                            "ไฟล์นี้เป็นแบบส่วนตัว (Private) หรือต้องการสิทธิ์เข้าถึง: โปรดตั้งค่าการแชร์ใน Google Drive เป็น 'ทุกคนที่มีลิงก์ (Anyone with the link)' ก่อนนำเข้า"
                        )
                    if resp.status_code != 200:
                        continue

                    # Handle virus scan / large file confirm prompt
                    if "confirm=" in resp.text and "<form" in resp.text:
                        token_match = re.search(r'name="confirm"\s+value="([^"]+)"', resp.text) or re.search(r'confirm=([0-9a-zA-Z_]+)', resp.text)
                        if token_match:
                            token = token_match.group(1)
                            confirm_url = f"https://drive.google.com/uc?export=download&id={item_id}&confirm={token}"
                            resp = client.get(confirm_url)

                    content = resp.content
                    if not content or len(content) < 30:
                        continue

                    # Check for Google HTML error pages disguised as 200
                    if resp.headers.get("content-type", "").startswith("text/html") and b"%PDF" not in content[:1024]:
                        if b"accounts.google.com" in content or b"Permission denied" in content or b"You need access" in content:
                            raise GoogleDriveImportError(
                                "ไฟล์นี้ต้องการสิทธิ์เข้าถึง (Permission required): โปรดเปิดการแชร์ใน Google Drive เป็น 'ทุกคนที่มีลิงก์' (Anyone with the link)"
                            )
                        # Maybe invalid id or non-downloadable file
                        continue

                    # Extract filename from Content-Disposition if present
                    cd = resp.headers.get("content-disposition", "")
                    filename = None
                    if "filename*=" in cd:
                        m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
                        if m:
                            filename = urllib.parse.unquote(m.group(1))
                    if not filename and "filename=" in cd:
                        m = re.search(r'filename="?([^";]+)"?', cd)
                        if m:
                            filename = m.group(1).strip()

                    if not filename:
                        filename = f"gdrive_quotation_{item_id[:8]}.pdf"
                    if not filename.lower().endswith(".pdf"):
                        filename += ".pdf"

                    clean_filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
                    temp_filename = f"stage_{unique_prefix}_{clean_filename}"
                    out_path = os.path.join(dest_dir, temp_filename)

                    with open(out_path, "wb") as f:
                        f.write(content)

                    return out_path, clean_filename

                except GoogleDriveImportError:
                    raise
                except Exception as e:
                    last_error = e
                    continue

            raise GoogleDriveImportError(
                f"ไม่สามารถดาวน์โหลดไฟล์ Google Drive ID: {item_id} ได้: {last_error or 'ตรวจสอบการแชร์ไฟล์เป็นสาธารณะ (Anyone with the link)'}"
            )
