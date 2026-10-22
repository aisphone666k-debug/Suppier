import sqlite3
from src.infrastructure.sqlite_manual_request_repository import SqliteManualRequestRepository
from src.application.slot_filling_agent import SlotFillingAgent


def test_slot_filling_flow():
    conn = sqlite3.connect(":memory:")
    repo = SqliteManualRequestRepository(conn)
    repo.initialize_schema()

    agent = SlotFillingAgent(manual_repo=repo)

    # 1. Trigger from empty search
    init_res = agent.trigger_from_empty_search("SES-TEST-1", "Mitsubishi PLC Q03UDE")
    assert init_res["step"] == "COLLECTING"
    assert init_res["slots"]["item_name"] == "Mitsubishi PLC Q03UDE"

    # 2. Provide missing details
    chat_res = agent.process_user_message(
        session_id="SES-TEST-1",
        user_message="Q03UDE CPU Module 30k Steps จำนวน 2 Pcs ด่วนมาก ฝ่ายผลิต Line 1",
        user_id="engineer_a",
    )

    assert chat_res["step"] == "COMPLETED"
    draft = chat_res["draft"]
    assert draft is not None
    assert draft["rfq_number"].startswith("PR-")
    assert draft["quantity"] == 2.0
    assert draft["unit"] == "Pcs"
    assert draft["urgency"] == "CRITICAL"
    assert "Line 1" in (draft["department"] or "")
