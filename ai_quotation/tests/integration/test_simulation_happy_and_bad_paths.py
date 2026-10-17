from datetime import date, timedelta
import io
import pytest
from fastapi.testclient import TestClient

from src.interfaces.web_app import create_app
from src.domain.quotation import QuotationId, QuotationStatus


@pytest.fixture
def simulation_client():
    app = create_app(db_path=":memory:", auto_seed=False)
    # Register 1 active quotation and 1 expired quotation
    app.state.service.register_quotation(
        quotation_number="ACT-001",
        vendor_name="Apex Precision Tools",
        issue_date=date.today() - timedelta(days=30),
        expiration_date=date.today() + timedelta(days=60),
        items=[
            {
                "item_number": 1,
                "part_number": "APX-CUT-10",
                "description": "Apex Carbide Cutting Tool 10mm",
                "quantity": 5.0,
                "unit": "Pcs",
                "unit_price": 1200.0,
            }
        ],
        pdf_path="quoatation/QT NO. 137836.pdf",
        pdf_sha256="sha_apex_001",
        user_role="PH_USER",
    )
    app.state.service.register_quotation(
        quotation_number="EXP-999",
        vendor_name="Past Era Equipment",
        issue_date=date.today() - timedelta(days=400),
        expiration_date=date.today() - timedelta(days=40),
        items=[
            {
                "item_number": 1,
                "part_number": "OLD-GEAR",
                "description": "Vintage Spur Gear 50T",
                "quantity": 2.0,
                "unit": "Pcs",
                "unit_price": 500.0,
            }
        ],
        pdf_path="quoatation/416359.pdf",
        pdf_sha256="sha_exp_999",
        user_role="PH_USER",
    )
    return TestClient(app)


# ==============================================================================
# BAD PATH SIMULATIONS
# ==============================================================================

def test_bad_path_receive_expired_quotation_fails_gracefully(simulation_client):
    """Attempting to receive an expired quotation must return 400 Bad Request with user feedback."""
    response = simulation_client.post(
        "/api/quotations/QT-EXP-999/receive",
        data={"user_id": "test_engineer"},
    )
    assert response.status_code == 400
    assert "expired" in response.text.lower()
    assert "[ERROR]" in response.text or "cannot be received" in response.text.lower()


def test_bad_path_receive_nonexistent_quotation_returns_404(simulation_client):
    """Attempting to receive a quotation that does not exist must return 404 Not Found."""
    response = simulation_client.post(
        "/api/quotations/QT-NONEXISTENT/receive",
        data={"user_id": "test_engineer"},
    )
    assert response.status_code == 404
    assert "not found" in response.text.lower()


def test_bad_path_renew_with_past_date_fails_gracefully(simulation_client):
    """Renewing with a past or today date must return 400 Bad Request with inline table error."""
    past_date = (date.today() - timedelta(days=5)).isoformat()
    response = simulation_client.post(
        "/api/quotations/QT-EXP-999/renew",
        data={
            "new_expiration_date": past_date,
            "remarks": "Invalid renewal attempt",
            "user_role": "PH_USER",
        },
    )
    assert response.status_code == 400
    assert "future" in response.text.lower() or "invalid" in response.text.lower()


def test_bad_path_renew_with_invalid_date_format_returns_400(simulation_client):
    """Renewing with an unparseable date format must return 400 Bad Request."""
    response = simulation_client.post(
        "/api/quotations/QT-EXP-999/renew",
        data={
            "new_expiration_date": "not-a-valid-date",
            "remarks": "Format failure",
            "user_role": "PH_USER",
        },
    )
    assert response.status_code == 400
    assert "date format" in response.text.lower() or "invalid" in response.text.lower()


def test_bad_path_normal_user_cannot_renew_quotation(simulation_client):
    """Normal users attempting quotation renewal must receive 403 Forbidden."""
    future_date = (date.today() + timedelta(days=90)).isoformat()
    response = simulation_client.post(
        "/api/quotations/QT-EXP-999/renew",
        data={
            "new_expiration_date": future_date,
            "remarks": "Unauthorized renewal attempt",
            "user_role": "NORMAL_USER",
        },
    )
    assert response.status_code == 403
    assert "only ph users" in response.text.lower() or "forbidden" in response.text.lower()


def test_bad_path_normal_user_cannot_register_quotation(simulation_client):
    """Normal users attempting quotation registration must receive 403 Forbidden."""
    pdf_content = b"%PDF-1.4 Fake dummy content for test"
    response = simulation_client.post(
        "/api/quotations/register",
        files={"pdf_file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"user_role": "NORMAL_USER"},
    )
    assert response.status_code == 403


def test_bad_path_fulfill_request_with_nonexistent_quotation_fails(simulation_client):
    """Fulfilling a demand ticket with a non-existent quotation ID must return 400 or 404."""
    # First create a valid manual request
    req_resp = simulation_client.post(
        "/api/requests/manual",
        data={
            "requester_user_id": "emp_01",
            "department": "Production",
            "item_description": "Custom Stamping Die",
        },
    )
    assert req_resp.status_code == 200
    import re
    match = re.search(r"REQ-[A-F0-9]{8}", req_resp.text)
    assert match is not None
    ticket_id = match.group(0)

    # Attempt to fulfill with phantom quotation ID
    fulfill_resp = simulation_client.post(
        f"/api/requests/{ticket_id}/fulfill",
        data={
            "quotation_id": "QT-GHOST-9999",
            "user_role": "PH_USER",
        },
    )
    assert fulfill_resp.status_code in (400, 404)
    assert "not found" in fulfill_resp.text.lower() or "invalid" in fulfill_resp.text.lower()


def test_bad_path_fulfill_request_by_normal_user_rejected(simulation_client):
    """Normal user cannot fulfill a manual demand ticket."""
    req_resp = simulation_client.post(
        "/api/requests/manual",
        data={
            "requester_user_id": "emp_01",
            "department": "Production",
            "item_description": "Hydraulic Hose 10m",
        },
    )
    import re
    ticket_id = re.search(r"REQ-[A-F0-9]{8}", req_resp.text).group(0)

    fulfill_resp = simulation_client.post(
        f"/api/requests/{ticket_id}/fulfill",
        data={
            "quotation_id": "QT-ACT-001",
            "user_role": "NORMAL_USER",
        },
    )
    assert fulfill_resp.status_code == 403


def test_bad_path_manual_request_empty_description_rejected(simulation_client):
    """Submitting empty or whitespace item description must return 400 Bad Request."""
    response = simulation_client.post(
        "/api/requests/manual",
        data={
            "requester_user_id": "emp_01",
            "department": "Production",
            "item_description": "   ",
        },
    )
    assert response.status_code == 400
    assert "empty" in response.text.lower() or "required" in response.text.lower()


def test_bad_path_manual_request_nonpositive_quantity_rejected(simulation_client):
    """Submitting target quantity <= 0 must return 400 Bad Request."""
    response = simulation_client.post(
        "/api/requests/manual",
        data={
            "requester_user_id": "emp_01",
            "department": "Production",
            "item_description": "Pneumatic Cylinder",
            "target_quantity": "-5.0",
        },
    )
    assert response.status_code == 400
    assert "positive" in response.text.lower() or "invalid" in response.text.lower()


def test_bad_path_corrupt_pdf_preview_handled_gracefully(simulation_client):
    """Uploading non-PDF or corrupt binary data to extract-preview returns 400 Bad Request."""
    corrupt_content = b"Not a valid PDF at all"
    response = simulation_client.post(
        "/api/quotations/extract-preview",
        files={"pdf_file": ("corrupt.pdf", io.BytesIO(corrupt_content), "application/pdf")},
        data={"user_role": "PH_USER"},
    )
    assert response.status_code == 400
    assert "pdf" in response.text.lower() or "corrupt" in response.text.lower() or "error" in response.json()
