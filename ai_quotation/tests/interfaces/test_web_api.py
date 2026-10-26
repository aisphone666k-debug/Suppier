import os
import time
from datetime import date
import pytest
from fastapi.testclient import TestClient

from src.interfaces.web_app import create_app
from src.domain.quotation import QuotationStatus


@pytest.fixture
def client():
    app = create_app(db_path=":memory:", auto_seed=False)
    # Seed 1 active and 1 expired quotation
    app.state.service.register_quotation(
        quotation_number="137836",
        vendor_name="Bando Chemical Industries Ltd.",
        issue_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "5V-1400",
                "description": "Power Ace V-Belt",
                "quantity": 10.0,
                "unit": "Pcs",
                "unit_price": 450.0,
            }
        ],
        pdf_path="quoatation/QT NO. 137836.pdf",
        pdf_sha256="sha137836",
        user_role="PH_USER",
    )
    app.state.service.register_quotation(
        quotation_number="OLD-999",
        vendor_name="Outdated Industrial Supplies",
        issue_date=date(2025, 1, 1),
        expiration_date=date(2025, 12, 31),
        items=[
            {
                "item_number": 1,
                "part_number": "OLD-PART",
                "description": "Legacy Sensor",
                "quantity": 1.0,
                "unit": "Pcs",
                "unit_price": 200.0,
            }
        ],
        pdf_path="quoatation/416359.pdf",
        pdf_sha256="sha416359",
        user_role="PH_USER",
    )
    return TestClient(app)


def test_home_page_renders_search_bar(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "QuotationFinder" in response.text
    assert "Search by part name" in response.text


def test_search_endpoint_returns_html_results_normal_user(client):
    response = client.post(
        "/search",
        data={"query": "rubber transmission belt", "user_role": "NORMAL_USER"},
    )
    assert response.status_code == 200
    # Should find active Bando quotation
    assert "137836" in response.text
    assert "Bando Chemical Industries Ltd." in response.text
    # Should NOT contain expired legacy quotation
    assert "OLD-999" not in response.text


def test_receive_quotation_endpoint(client):
    response = client.post(
        "/api/quotations/QT-137836/receive",
        data={"user_id": "emp_john"},
    )
    assert response.status_code == 200
    assert "successfully received" in response.text.lower()


def test_manual_request_submission(client):
    response = client.post(
        "/api/requests/manual",
        data={
            "requester_user_id": "emp_john",
            "department": "Engineering",
            "item_description": "Custom Mold Flange 250mm",
            "part_number": "FLG-250",
            "target_quantity": "5",
            "target_unit": "Pcs",
            "needed_by_date": "2026-11-20",
            "urgency": "HIGH",
        },
    )
    assert response.status_code == 200
    assert "REQ-" in response.text
    assert "submitted successfully" in response.text.lower()


def test_ph_portal_and_renewal_flow(client):
    # Check expired list in PH portal
    portal_resp = client.get("/ph-portal")
    assert portal_resp.status_code == 200
    assert "OLD-999" in portal_resp.text

    # Renew expired quotation
    renew_resp = client.post(
        "/api/quotations/QT-OLD-999/renew",
        data={
            "new_expiration_date": "2027-12-31",
            "remarks": "Extended contract",
            "user_role": "PH_USER",
        },
    )
    assert renew_resp.status_code == 200
    assert "renewed successfully" in renew_resp.text.lower()

    # Now Normal user should be able to find it
    search_resp = client.post(
        "/search",
        data={"query": "Legacy Sensor", "user_role": "NORMAL_USER"},
    )
    assert search_resp.status_code == 200
    assert "OLD-999" in search_resp.text


def test_smart_extract_preview_endpoint(client):
    import os
    pdf_path = os.path.join("quoatation", "26Q13131 (2).pdf")
    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/api/quotations/extract-preview",
            files={"pdf_file": ("26Q13131 (2).pdf", f, "application/pdf")},
            data={"user_role": "PH_USER"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quotation_number"] == "26Q13131"
    assert "IWASE" in data["vendor_name"]
    assert data["issue_date"] == "2026-07-31"
    assert "items" in data
    assert len(data["items"]) >= 1


def test_smart_register_with_auto_extracted_fields(client):
    import os
    pdf_path = os.path.join("quoatation", "26DD09113 _ Botton Box  Project M-AL6-001B__ (PMC_Minebea Thai) K. Peerapat.pdf")
    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/api/quotations/register",
            files={"pdf_file": ("26DD09113.pdf", f, "application/pdf")},
            data={
                "user_role": "PH_USER",
                # Omit quotation_number, vendor_name, dates, items -> auto extract!
            },
            follow_redirects=False,
        )
    # Redirects to /ph-portal on success
    assert resp.status_code in [302, 303]
    assert resp.headers["location"] == "/ph-portal"

    # Verify indexed and searchable
    search_resp = client.post(
        "/search",
        data={"query": "Botton Box", "user_role": "NORMAL_USER"},
    )
    assert search_resp.status_code == 200
    assert "26DD09113" in search_resp.text or "DooDee" in search_resp.text


def test_inquiry_ask_endpoint(client, monkeypatch):
    from unittest.mock import MagicMock
    from src.application.inquiry_generator import AnswerGeneratorPort

    class MockGen(AnswerGeneratorPort):
        def generate_answer(self, query, context_chunks):
            return "Based on quotation 137836, the Power Ace V-Belt is 450.0 THB."

    client.app.state.inquiry_service.answer_generator = MockGen()

    resp = client.post(
        "/api/inquiry/ask",
        data={"query": "What is the price of Bando belt?", "user_role": "NORMAL_USER"},
    )
    assert resp.status_code == 200
    assert "450.0 THB" in resp.text
    assert "AI Procurement Assistant" in resp.text
    assert "Referenced Quotations" in resp.text
    assert "Research" in resp.text
    assert "PDF" in resp.text


def test_batch_register_endpoint(client):
    import os
    pdf1 = os.path.join("quoatation", "QT NO. 137836.pdf")
    pdf2 = os.path.join("quoatation", "26Q13131 (2).pdf")

    with open(pdf1, "rb") as f1, open(pdf2, "rb") as f2:
        resp = client.post(
            "/api/quotations/batch-register",
            files=[
                ("pdf_files", ("QT NO. 137836.pdf", f1, "application/pdf")),
                ("pdf_files", ("26Q13131 (2).pdf", f2, "application/pdf")),
            ],
            data={"user_role": "PH_USER"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_files"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2
    assert any("FANUC" in r["vendor_name"] or "137836" in r["quotation_number"] for r in data["results"])


def test_batch_preview_and_commit_with_user_edits(client):
    import os
    pdf1 = os.path.join("quoatation", "QT NO. 137836.pdf")

    with open(pdf1, "rb") as f1:
        preview_resp = client.post(
            "/api/quotations/batch-preview",
            files=[
                ("pdf_files", ("QT NO. 137836.pdf", f1, "application/pdf")),
            ],
            data={"user_role": "PH_USER"},
        )
    assert preview_resp.status_code == 200
    pdata = preview_resp.json()
    assert pdata["total_files"] == 1
    draft = pdata["drafts"][0]
    assert "137836" in draft["quotation_number"]
    assert len(draft["items"]) >= 1

    # Simulate user editing the quotation fields & line item before committing
    commit_payload = {
        "user_role": "PH_USER",
        "quotations": [
            {
                "staging_id": draft["staging_id"],
                "temp_file_path": draft["temp_file_path"],
                "filename": draft["filename"],
                "quotation_number": "137836-EDITED",
                "vendor_name": "FANUC THAI (CUSTOM EDITED)",
                "vendor_tax_id": "0105537025801",
                "issue_date": "2026-03-01",
                "expiration_date": "2026-12-31",
                "currency": "THB",
                "items": [
                    {
                        "item_number": 1,
                        "part_number": "CUSTOM-PART-9999",
                        "description": "Special High Precision CNC Cable",
                        "quantity": 3.0,
                        "unit": "Sets",
                        "unit_price": 9500.0,
                    }
                ],
            }
        ],
    }

    commit_resp = client.post(
        "/api/quotations/batch-commit",
        json=commit_payload,
    )
    assert commit_resp.status_code == 200
    cdata = commit_resp.json()
    assert cdata["successful"] == 1
    assert cdata["failed"] == 0

    # Search for user-edited part number and custom description
    search_resp = client.post(
        "/search",
        data={"query": "CUSTOM-PART-9999", "user_role": "NORMAL_USER"},
    )
    assert search_resp.status_code == 200
    assert "137836-EDITED" in search_resp.text
    assert "FANUC THAI (CUSTOM EDITED)" in search_resp.text
    assert "CUSTOM-PART-9999" in search_resp.text


def test_ask_inquiry_json_endpoint(client):
    response = client.post(
        "/api/inquiry/ask-json",
        data={"query": "belt", "user_role": "NORMAL_USER"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "cached" in data
    assert "total_duration_ms" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)


def test_extract_preview_empty_file_returns_clear_error(client):
    resp = client.post(
        "/api/quotations/extract-preview",
        files={"pdf_file": ("empty.pdf", b"", "application/pdf")},
        data={"user_role": "PH_USER"},
    )
    assert resp.status_code == 400
    assert "empty (0 bytes)" in resp.json()["detail"]


def test_batch_preview_empty_file_handled_without_leaving_zero_byte_file(client):
    import glob
    resp = client.post(
        "/api/quotations/batch-preview",
        files=[("pdf_files", ("empty.pdf", b"", "application/pdf"))],
        data={"user_role": "PH_USER"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_files"] == 1
    assert "empty" in data["drafts"][0]["warning"].lower()

    # Ensure no 0-byte stage files linger in staging
    zero_files = [f for f in glob.glob("storage/staging/stage_*empty.pdf") if os.path.getsize(f) == 0]
    assert len(zero_files) == 0


def test_cleanup_old_staging():
    from src.interfaces.web_app import _cleanup_old_staging
    os.makedirs("storage/staging", exist_ok=True)
    dummy_old = os.path.join("storage", "staging", "stage_test_old.pdf")
    with open(dummy_old, "wb") as f:
        f.write(b"test")
    # Set mtime to 2 hours ago
    past = time.time() - 7200
    os.utime(dummy_old, (past, past))

    _cleanup_old_staging(max_age_seconds=1800)
    assert not os.path.exists(dummy_old)


def test_gdrive_import_endpoint_validation_and_flow(client):
    from unittest.mock import patch

    # 1. Non-PH user is rejected with 403
    resp_403 = client.post(
        "/api/quotations/gdrive-import",
        json={"user_role": "NORMAL_USER", "url": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OIvE2e144/view"},
    )
    assert resp_403.status_code == 403

    # 2. Empty input is rejected with 400
    resp_empty = client.post(
        "/api/quotations/gdrive-import",
        json={"user_role": "PH_USER", "raw_text": ""},
    )
    assert resp_empty.status_code == 400

    # 3. Valid link with mocked download
    sample_pdf = os.path.join("quoatation", "QT NO. 137836.pdf")
    with patch("src.infrastructure.google_drive_importer.GoogleDriveImporter.download_gdrive_pdf") as mock_dl:
        mock_dl.return_value = (sample_pdf, "Quotation_Fanuc.pdf")

        resp_ok = client.post(
            "/api/quotations/gdrive-import",
            json={
                "user_role": "PH_USER",
                "raw_text": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OIvE2e144/view?usp=sharing",
            },
        )
        assert resp_ok.status_code == 200
        data = resp_ok.json()
        assert data["total_files"] == 1
        assert data["successful"] == 1
        assert len(data["drafts"]) == 1
        draft = data["drafts"][0]
        assert "137836" in draft["quotation_number"]
        assert len(draft["items"]) >= 1

    # 4. Folder with no files raises informative 400
    with patch("src.infrastructure.google_drive_importer.GoogleDriveImporter.fetch_folder_file_ids", return_value=[]):
        resp_empty_folder = client.post(
            "/api/quotations/gdrive-import",
            json={
                "user_role": "PH_USER",
                "raw_text": "https://drive.google.com/drive/folders/1ALajU3I5oWp0GFNznYJvwdJg8gCbuM3A",
            },
        )
        assert resp_empty_folder.status_code == 400
        assert "ไม่สามารถดึงรายการไฟล์จากโฟลเดอร์ Google Drive" in resp_empty_folder.json()["detail"]
