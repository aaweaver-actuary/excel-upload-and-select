"""Exercise the real HTTP flow through the frontend proxy; Python stdlib only."""
import json
import sys
import urllib.error
import urllib.request


def request(base, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=body, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.read().decode()


def main(base):
    status, body = request(base, "/")
    assert status == 200 and '<div id="root">' in body
    assert json.loads(request(base, "/api/health")[1]) == {"status": "ok"}
    schema = json.loads(request(base, "/api/schema")[1])
    assert len(schema["fields"]) == 6
    columns = [{"id": "A", "label": "First Name"}, {"id": "C", "label": "Emial"}]
    status, body = request(base, "/api/match-columns", {"columns": columns})
    assert status == 200
    suggestions = {item["fieldKey"]: item for item in json.loads(body)["suggestions"]}
    assert suggestions["firstName"]["matchType"] == "exact"
    assert suggestions["email"]["matchType"] == "fuzzy"
    data = {"columns": columns, "rows": [{"A": f" Person {index} ", "C": " x@example.com "} for index in range(12)], "mapping": {"firstName": "A", "email": "C"}}
    assert request(base, "/api/process", data)[0] == 422
    status, body = request(base, "/api/process", data | {"confirmedFields": ["email"]})
    result = json.loads(body)
    assert status == 200 and result["rowsReceived"] == result["rowsProcessed"] == 12
    assert len(result["previewRows"]) == 10
    assert result["previewRows"][0]["firstName"] == "Person 0"
    assert result["nonEmptyCounts"]["email"] == 12
    print("Compose smoke test passed: frontend, proxy, schema, matching, approval, and all-row processing.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080")
