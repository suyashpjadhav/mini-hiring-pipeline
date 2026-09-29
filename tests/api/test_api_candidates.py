"""API tests for candidate endpoints, transitions, notes, and verification (TEST_PLAN Step 9)."""

from fastapi.testclient import TestClient

from app.features.pipeline.domain.stages import Stage, Status


def test_candidate_endpoints_and_status_codes(client: TestClient) -> None:
    """Test candidate lifecycle via API endpoints including creation, transitions, and errors."""
    # 1. Create candidate with email
    resp = client.post(
        "/api/v1/candidates",
        json={"full_name": "Test Candidate", "email": "test@example.com"},
    )
    assert resp.status_code == 201
    cand1 = resp.json()
    cand1_id = cand1["id"]
    assert cand1["full_name"] == "Test Candidate"
    assert cand1["email"] == "test@example.com"
    assert cand1["stage"] == Stage.APPLIED.value
    assert cand1["status"] == Status.ACTIVE.value
    assert cand1["version"] == 1

    # 2. Create candidate without email
    resp_no_email = client.post("/api/v1/candidates", json={"full_name": "No Email Candidate"})
    assert resp_no_email.status_code == 201
    cand2 = resp_no_email.json()
    assert cand2["email"] is None

    # 3. List board
    resp_board = client.get("/api/v1/candidates")
    assert resp_board.status_code == 200
    board = resp_board.json()
    assert len(board["applied"]) == 2

    # 4. Get candidate detail
    resp_detail = client.get(f"/api/v1/candidates/{cand1_id}")
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["candidate"]["id"] == cand1_id
    assert len(detail["events"]) == 1
    assert detail["events"][0]["type"] == "CREATED"
    assert detail["chain_valid"] is True

    # 5. Advance through to Hired (Applied -> Screening -> Interview -> Offer -> Hired)
    # Applied -> Screening (expected_version=1)
    resp_t1 = client.post(
        f"/api/v1/candidates/{cand1_id}/transitions",
        json={"action": "advance", "expected_version": 1},
    )
    assert resp_t1.status_code == 200
    assert resp_t1.json()["stage"] == Stage.SCREENING.value
    assert resp_t1.json()["version"] == 2

    # Screening -> Interview (expected_version=2)
    resp_t2 = client.post(
        f"/api/v1/candidates/{cand1_id}/transitions",
        json={"action": "advance", "expected_version": 2},
    )
    assert resp_t2.status_code == 200
    assert resp_t2.json()["stage"] == Stage.INTERVIEW.value
    assert resp_t2.json()["version"] == 3

    # Interview -> Offer (expected_version=3)
    resp_t3 = client.post(
        f"/api/v1/candidates/{cand1_id}/transitions",
        json={"action": "advance", "expected_version": 3},
    )
    assert resp_t3.status_code == 200
    assert resp_t3.json()["stage"] == Stage.OFFER.value
    assert resp_t3.json()["version"] == 4

    # Offer -> Hired (expected_version=4)
    resp_t4 = client.post(
        f"/api/v1/candidates/{cand1_id}/transitions",
        json={"action": "advance", "expected_version": 4},
    )
    assert resp_t4.status_code == 200
    assert resp_t4.json()["stage"] == Stage.HIRED.value
    assert resp_t4.json()["status"] == Status.HIRED.value
    assert resp_t4.json()["version"] == 5

    # 6. Attempting to advance a Hired candidate -> 409 FINAL_OUTCOME
    resp_final = client.post(
        f"/api/v1/candidates/{cand1_id}/transitions",
        json={"action": "advance", "expected_version": 5},
    )
    assert resp_final.status_code == 409
    assert resp_final.json()["code"] == "FINAL_OUTCOME"

    # 7. Reject candidate
    cand3_resp = client.post("/api/v1/candidates", json={"full_name": "Reject User"})
    cand3_id = cand3_resp.json()["id"]

    resp_rej = client.post(
        f"/api/v1/candidates/{cand3_id}/transitions",
        json={
            "action": "reject",
            "expected_version": 1,
            "note": "Failed screening test",
        },
    )
    assert resp_rej.status_code == 200
    assert resp_rej.json()["status"] == Status.REJECTED.value

    # 8. Stale expected_version -> 409 STALE_VERSION
    cand4_resp = client.post("/api/v1/candidates", json={"full_name": "Stale User"})
    cand4_id = cand4_resp.json()["id"]

    resp_stale = client.post(
        f"/api/v1/candidates/{cand4_id}/transitions",
        json={"action": "advance", "expected_version": 99},
    )
    assert resp_stale.status_code == 409
    assert resp_stale.json()["code"] == "STALE_VERSION"

    # 9. Duplicate email -> 409 DUPLICATE_EMAIL
    client.post(
        "/api/v1/candidates",
        json={"full_name": "Email Unique", "email": "unique@example.com"},
    )
    resp_dup = client.post(
        "/api/v1/candidates",
        json={"full_name": "Email Duplicate", "email": "unique@example.com"},
    )
    assert resp_dup.status_code == 409
    assert resp_dup.json()["code"] == "DUPLICATE_EMAIL"

    # 10. Unknown id and malformed id -> 404 NOT_FOUND
    unknown_ulid = "01H00000000000000000000000"
    resp_unk = client.get(f"/api/v1/candidates/{unknown_ulid}")
    assert resp_unk.status_code == 404
    assert resp_unk.json()["code"] == "NOT_FOUND"

    resp_malformed = client.get("/api/v1/candidates/invalid-ulid-format")
    assert resp_malformed.status_code == 404
    assert resp_malformed.json()["code"] == "NOT_FOUND"

    # 11. Notes 201
    resp_note = client.post(
        f"/api/v1/candidates/{cand1_id}/notes",
        json={"note": "Added candidate reference note"},
    )
    assert resp_note.status_code == 201
    note_evt = resp_note.json()
    assert note_evt["type"] == "NOTE"
    assert note_evt["note"] == "Added candidate reference note"

    # 12. Verify
    resp_v = client.get(f"/api/v1/candidates/{cand1_id}/verify")
    assert resp_v.status_code == 200
    v_data = resp_v.json()
    assert v_data["candidate_id"] == cand1_id
    assert v_data["valid"] is True
    assert v_data["broken_at_seq"] is None
