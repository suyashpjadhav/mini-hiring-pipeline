"""API route inventory test proving no mutation endpoints exist (TEST_PLAN Step 9)."""

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


def test_api_route_inventory_no_mutation(client: TestClient) -> None:
    """Verify route inventory contains no PUT, PATCH, or DELETE endpoints."""
    assert isinstance(client.app, FastAPI)
    app: FastAPI = client.app
    forbidden_methods = {"PUT", "PATCH", "DELETE"}
    allowed_post_paths = {
        "/api/v1/candidates",
        "/api/v1/candidates/{id}/transitions",
        "/api/v1/candidates/{id}/notes",
    }

    for route in app.routes:
        if isinstance(route, APIRoute) and route.methods is not None:
            methods: set[str] = route.methods
            path: str = route.path

            for method in methods:
                msg = f"Forbidden HTTP method {method} found on route '{path}'"
                assert method not in forbidden_methods, msg

            if "POST" in methods:
                msg = f"Unexpected POST route found on path '{path}'"
                assert path in allowed_post_paths, msg
