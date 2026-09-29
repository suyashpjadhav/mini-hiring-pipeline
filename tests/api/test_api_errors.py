"""API error formatting and Pydantic validation 422 to 400 remapping tests (TEST_PLAN Step 9)."""

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient


def test_api_error_formatting_and_422_remap(client: TestClient) -> None:
    """Test error formatting for domain errors, validation errors, and 500 internal errors."""
    # 1. Missing field on candidate create -> 400 with details
    resp_missing = client.post("/api/v1/candidates", json={})
    assert resp_missing.status_code == 400
    data_missing = resp_missing.json()
    assert data_missing["code"] == "INVALID_INPUT"
    assert "full_name" in data_missing["message"]
    assert len(data_missing["details"]) >= 1

    # 2. Extra field in TransitionRequest -> 400 (forbidden extra field)
    # create candidate first
    cand_resp = client.post("/api/v1/candidates", json={"full_name": "Valid Candidate"})
    cand_id = cand_resp.json()["id"]

    resp_extra = client.post(
        f"/api/v1/candidates/{cand_id}/transitions",
        json={"action": "advance", "expected_version": 1, "to_stage": "Hired"},
    )
    assert resp_extra.status_code == 400
    data_extra = resp_extra.json()
    assert data_extra["code"] == "INVALID_INPUT"
    assert "to_stage" in data_extra["message"]

    # 3. Invalid action ("skip") -> 400
    resp_invalid_action = client.post(
        f"/api/v1/candidates/{cand_id}/transitions",
        json={"action": "skip", "expected_version": 1},
    )
    assert resp_invalid_action.status_code == 400
    data_inv = resp_invalid_action.json()
    assert data_inv["code"] == "INVALID_INPUT"

    # 4. Domain error formatting: test shape {code, message, hint}
    resp_stale = client.post(
        f"/api/v1/candidates/{cand_id}/transitions",
        json={"action": "advance", "expected_version": 999},
    )
    assert resp_stale.status_code == 409
    data_stale = resp_stale.json()
    assert data_stale["code"] == "STALE_VERSION"
    assert "message" in data_stale
    assert "hint" in data_stale

    # 5. Unhandled 500 exception handler hides internals
    assert isinstance(client.app, FastAPI)
    test_router = APIRouter(prefix="/api/v1")

    @test_router.get("/error_test_500")
    def raise_500() -> None:
        raise RuntimeError("Sensitive internal database connection string error")

    client.app.include_router(test_router)

    with TestClient(client.app, raise_server_exceptions=False) as err_client:
        resp_500 = err_client.get("/api/v1/error_test_500")
        assert resp_500.status_code == 500
        data_500 = resp_500.json()
        assert data_500 == {"code": "INTERNAL_ERROR", "message": "Something went wrong."}
        assert "Sensitive" not in resp_500.text
