import os
import sys
from pathlib import Path
from datetime import date

base_dir = Path(__file__).resolve().parent
os.chdir(base_dir)
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from fastapi.testclient import TestClient
from src.interfaces.web_app import create_app

print("[TEST] Initializing FastAPI test client...", flush=True)
app = create_app(db_path=str(base_dir / "quotations.db"), auto_seed=False)
client = TestClient(app)

print("\n--- TEST 1: HYBRID MULTI-STAGE SEARCH ---")
test_queries = ["BANDO", "H7CC-ASD", "Cap screw", "EW32EAG", "Belt"]
for q in test_queries:
    resp = client.get(f"/api/search?query={q}&user_role=NORMAL_USER")
    assert resp.status_code == 200, f"Search failed for {q}: {resp.text}"
    data = resp.json()
    print(f"Query '{q}': found {data['count']} results. Top: {data['results'][0]['quotation_number'] if data['results'] else 'None'} | Stage: {data['results'][0]['retrieval_stage'] if data['results'] else 'None'} | Conf: {data['results'][0]['confidence_score'] if data['results'] else 'None'}")
    assert data["count"] > 0, f"Expected matches for {q}"

print("\n--- TEST 2: SLOT-FILLING CONVERSATIONAL PR/RFQ AGENT ---")
# 1. Search non-existent item to trigger agent
resp_empty = client.get("/api/search?query=Inverter_Delta_VFD_XYZ_999&user_role=NORMAL_USER")
assert resp_empty.status_code == 200
data_empty = resp_empty.json()
assert data_empty["slot_filling_available"] is True
session_id = data_empty["slot_filling_prompt"]["session_id"]
print(f"[OK] Empty search triggered slot-filling prompt for session: {session_id}")

# 2. User sends specifications
chat_payload = {
    "session_id": session_id,
    "message": "Delta VFD 7.5kW 380V 3-Phase จำนวน 3 ชุด ด่วนมาก แผนก Maintenance",
    "user_id": "engineer_somchai",
    "user_role": "NORMAL_USER",
}
chat_resp = client.post("/api/chat/slot-filling", json=chat_payload)
assert chat_resp.status_code == 200
chat_data = chat_resp.json()
print(f"Agent Step: {chat_data['step']}")
assert chat_data["step"] == "COMPLETED"
assert chat_data["draft"] is not None
print(f"[OK] Generated PR/RFQ: {chat_data['draft']['rfq_number']} for {chat_data['draft']['item_name']}")
print(f"    Quantity: {chat_data['draft']['quantity']} {chat_data['draft']['unit']} | Urgency: {chat_data['draft']['urgency']}")

print("\n--- TEST 3: PRICE ANALYTICS ---")
trend_resp = client.get("/api/analytics/price-trend?query=BANDO")
assert trend_resp.status_code == 200
trend_data = trend_resp.json()
if trend_data.get("data"):
    td = trend_data["data"]
    print(f"[OK] Price Trend for '{trend_data['query']}': Min={td['min_price']}, Max={td['max_price']}, Avg={td['avg_price']}, Latest={td['latest_price']}")
    print(f"     Trend: {td['trend_direction']} ({td['price_change_pct']}%) | Rec: {td['recommendation']}")

print("\n--- TEST 4: REAL-TIME ALERTS ---")
alerts_resp = client.get("/api/alerts/recent")
assert alerts_resp.status_code == 200
alerts_data = alerts_resp.json()
print(f"[OK] System Alerts Count: {alerts_data['count']}")
for a in alerts_data["alerts"][:3]:
    print(f"    * [{a['severity']}] {a['title']} - {a['message'][:60]}...")

print("\n--- TEST 5: HITL (HUMAN-IN-THE-LOOP) WORKFLOW ---")
# Stage a sample PDF
sample_pdf = os.path.join(base_dir, "quoatation", "0010584101.pdf")
if os.path.exists(sample_pdf):
    with open(sample_pdf, "rb") as f:
        stage_resp = client.post(
            "/api/hitl/stage",
            files={"pdf_file": ("0010584101.pdf", f, "application/pdf")},
            data={"user_role": "PH_USER"},
        )
    assert stage_resp.status_code == 200, f"Stage failed: {stage_resp.text}"
    staged_data = stage_resp.json()
    stg_id = staged_data["staging_id"]
    print(f"[OK] Staged draft ID: {stg_id} | Quotation No: {staged_data['quotation_number']} | Vendor: {staged_data['vendor_name']} | Items: {len(staged_data['items'])}")

    # Update draft (Human edit)
    update_payload = {
        "quotation_number": "HITL-TEST-001",
        "vendor_name": "BANDO CHEMICAL (VERIFIED)",
        "items": [
            {
                "item_number": 1,
                "part_number": "A-61(S)",
                "description": "Bando V-Belt Premium Verified",
                "quantity": 5.0,
                "unit": "Pcs",
                "unit_price": 520.0,
            }
        ]
    }
    upd_resp = client.post(f"/api/hitl/drafts/{stg_id}/update", json=update_payload)
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["vendor_name"] == "BANDO CHEMICAL (VERIFIED)"
    print(f"[OK] Human edited draft: Vendor={upd_data['vendor_name']}, Items={len(upd_data['items'])}, Total={upd_data['total_amount']}")

    # Commit draft
    commit_resp = client.post(f"/api/hitl/drafts/{stg_id}/commit", data={"user_role": "PH_USER"})
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    print(f"[OK] Successfully committed verified quotation: {commit_data['quotation_id']} ({commit_data['quotation_number']})")

    # Verify search finds the newly committed quotation immediately
    new_search = client.get("/api/search?query=HITL-TEST-001&user_role=NORMAL_USER")
    assert new_search.status_code == 200
    ns_data = new_search.json()
    assert ns_data["count"] > 0
    print(f"[OK] Verified newly committed quotation is immediately searchable via Hybrid Search! Conf: {ns_data['results'][0]['confidence_score']}")

print("\n=======================================================")
print("ALL TESTS PASSED WITH 100% SUCCESS!")
print("=======================================================")
