import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.columns import FIELDS, SETTINGS, Field
from app.main import RequestSizeLimit, app, create_app


@pytest.fixture
def client():
    return TestClient(create_app(FIELDS))


def test_health_schema_and_documentation(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    schema = client.get("/api/schema").json()
    assert [field["key"] for field in schema["fields"]] == [field.key for field in FIELDS]
    assert all(not field["required"] for field in schema["fields"])
    assert schema["settings"]["max_rows"] == 50_000
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_end_to_end_exact_and_approved_fuzzy_import(client):
    columns = [{"id": "A", "label": "First Name"}, {"id": "C", "label": "Emial"}]
    response = client.post("/api/match-columns", json={"columns": columns})
    assert response.status_code == 200
    suggestions = {item["fieldKey"]: item for item in response.json()["suggestions"]}
    assert suggestions["firstName"]["matchType"] == "exact"
    assert suggestions["email"]["matchType"] == "fuzzy"
    data = {"columns": columns, "rows": [{"A": " Ada ", "C": " a@example.com "}] * 12, "mapping": {"firstName": "A", "email": "C"}}
    assert client.post("/api/process", json=data).status_code == 422
    response = client.post("/api/process", json=data | {"confirmedFields": ["email"]})
    assert response.status_code == 200
    assert response.json()["rowsProcessed"] == 12
    assert response.json()["previewRows"][0]["firstName"] == "Ada"


def test_duplicate_column_ids_and_invalid_payloads(client):
    duplicate = {"columns": [{"id": "A", "label": "Email"}, {"id": "A", "label": "Phone"}]}
    response = client.post("/api/match-columns", json=duplicate)
    assert response.status_code == 422 and "unique" in response.json()["detail"]
    assert client.post("/api/match-columns", json={"columns": []}).status_code == 422
    assert client.post("/api/process", json={}).status_code == 422
    assert client.post("/api/process", content="broken json").status_code == 422


def test_custom_schema_reaches_matching_and_processing():
    client = TestClient(create_app((Field("custom", "Custom", ("alternate",), True),), replace(SETTINGS, max_rows=1)))
    assert client.get("/api/schema").json()["fields"][0]["required"] is True
    data = {"columns": [{"id": "B", "label": "Alternate"}], "rows": [{"B": 42}], "mapping": {"custom": "B"}}
    assert client.post("/api/process", json=data).json()["previewRows"] == [{"custom": 42}]


def test_body_limit_is_enforced_before_parsing():
    client = TestClient(create_app(settings=replace(SETTINGS, max_request_bytes=10)))
    response = client.post("/api/process", content="x" * 11)
    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_size_middleware_handles_chunking_boundaries_disconnect_and_non_http():
    async def scenario():
        for scope_type, messages, expected_calls in [
            ("websocket", [], 1),
            ("http", [{"type": "http.disconnect"}], 0),
            ("http", [{"type": "http.request", "body": b"12", "more_body": True}, {"type": "http.request", "body": b"345", "more_body": False}], 1),
            ("http", [{"type": "http.request", "body": b"12", "more_body": True}, {"type": "http.request", "body": b"3456", "more_body": False}], 0),
        ]:
            receive = AsyncMock(side_effect=messages)
            send = AsyncMock()
            application = AsyncMock()
            if scope_type == "http" and expected_calls:
                async def drain(scope, replay, send):
                    assert (await replay())["body"] == b"12"
                    assert (await replay())["body"] == b"345"
                application.side_effect = drain
            await RequestSizeLimit(application, 5)({"type": scope_type}, receive, send)
            assert application.await_count == expected_calls
            if scope_type == "http" and len(messages) == 2 and not expected_calls:
                assert send.await_args_list[0].args[0]["status"] == 413
    asyncio.run(scenario())
