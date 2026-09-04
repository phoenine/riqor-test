import httpx
import pytest

from rigorpath_api_test import ApiSession


def test_executes_asserts_captures_and_cleans_up():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(201, json={"id": 7, "state": "created"})

    case = {
        "id": "AUTO-001",
        "request": {"method": "POST", "path": "/items", "json": {"name": "demo"}},
        "assertions": [
            {
                "type": "requirement",
                "source": "REQ-001",
                "target": "status",
                "matcher": "eq",
                "expected": 201,
            },
            {
                "type": "requirement",
                "source": "REQ-001",
                "target": "jsonpath",
                "path": "$.state",
                "matcher": "eq",
                "expected": "created",
            },
        ],
        "capture": [{"name": "item_id", "path": "$.id"}],
        "cleanup": {"method": "DELETE", "path": "/items/${cache.item_id}"},
    }
    with ApiSession(
        "https://example.test", transport=httpx.MockTransport(handler)
    ) as session:
        result = session.execute(case)
        assert result.status_code == 201
        assert session.cache["item_id"] == 7
    assert requests == [("POST", "/items"), ("DELETE", "/items/7")]


def test_cleanup_failure_is_not_hidden():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500 if request.method == "DELETE" else 200, json={})

    case = {
        "id": "AUTO-001",
        "request": {"method": "GET", "path": "/items"},
        "assertions": [
            {
                "type": "contract",
                "source": "OpenAPI GET /items",
                "target": "status",
                "matcher": "eq",
                "expected": 200,
            }
        ],
        "cleanup": {"method": "DELETE", "path": "/items/7"},
    }
    with ApiSession(
        "https://example.test", transport=httpx.MockTransport(handler)
    ) as session:
        with pytest.raises(AssertionError, match="cleanup returned HTTP 500"):
            session.execute(case)
