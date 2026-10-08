"""Verify durable XLSX processing through Nginx with Python's standard library."""
from io import BytesIO
import json
import time
import urllib.error
import urllib.request
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def request(base, path, body=None, content_type="application/json"):
    req = urllib.request.Request(base + path, data=body, headers={"Content-Type": content_type})
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.read()


def fixture():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Accounts" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        rows = ['<row r="1"><c r="A1" t="inlineStr"><is><t>Business Name</t></is></c></row>']
        for number in range(2, 14):
            rows.append(f'<row r="{number}"><c r="A{number}" t="inlineStr"><is><t> Account {number} </t></is></c></row>')
        archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(rows) + '</sheetData></worksheet>')
    return buffer.getvalue()


def main(base):
    assert request(base, "/")[0] == 200
    assert json.loads(request(base, "/api/health")[1]) == {"status": "ok"}
    deadline = time.monotonic() + 30
    while request(base, "/api/ready")[0] != 200:
        assert time.monotonic() < deadline, "Worker did not become ready"
        time.sleep(0.5)
    schema = json.loads(request(base, "/api/schema")[1])
    assert any(field["key"] == "business_name" and field["required"] for field in schema["fields"])
    matches = json.loads(request(base, "/api/match-columns", json.dumps({"columns": [{"id": "A", "label": "Business Name"}]}).encode())[1])
    assert next(item for item in matches["suggestions"] if item["fieldKey"] == "business_name")["matchType"] == "exact"
    boundary = "batch-smoke-boundary"
    metadata = json.dumps({"sheet_name": "Accounts", "mapping": {"business_name": "A"}})
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n{metadata}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="fixture.xlsx"\r\n'
            'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode()
    body += fixture() + f'\r\n--{boundary}--\r\n'.encode()
    status, accepted = request(base, "/api/v1/jobs", body, f"multipart/form-data; boundary={boundary}")
    assert status == 202, accepted.decode()
    job_id = json.loads(accepted)["job_id"]
    deadline = time.monotonic() + 30
    while True:
        job = json.loads(request(base, f"/api/v1/jobs/{job_id}")[1])
        if job["status"] in {"completed", "completed_with_issues", "failed"}:
            break
        assert time.monotonic() < deadline, "Job did not complete"
        time.sleep(0.5)
    assert job["status"] == "completed_with_issues" and job["total_rows"] == job["processed_rows"] == 12
    assert job["scored_rows"] == 0 and job["needs_review_rows"] == 12
    status, result_rows = request(base, f"/api/v1/jobs/{job_id}/rows?limit=5&status=needs_review")
    assert status == 200
    result_rows = json.loads(result_rows)
    assert result_rows["total"] == 12 and len(result_rows["rows"]) == 5
    for number, row in enumerate(result_rows["rows"], 2):
        assert row["source_row_number"] == number
        assert row["canonical_account"]["business_name"] == f"Account {number}"
        assert "SCORING_NOT_CONFIGURED" in row["issues"]
    status, last_rows = request(base, f"/api/v1/jobs/{job_id}/rows?offset=10&limit=5")
    assert status == 200 and [row["source_row_number"] for row in json.loads(last_rows)["rows"]] == [12, 13]
    status, result = request(base, f"/api/v1/jobs/{job_id}/result")
    assert status == 200
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(BytesIO(result)) as archive:
        rows = ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall("s:sheetData/s:row", namespace)
        assert len(rows) == 13
        for number, row in enumerate(rows[1:], 2):
            assert row.find("s:c/s:is/s:t", namespace).text == f" Account {number} "
            assert row.findall("s:c", namespace)[1].find("s:v", namespace).text == str(number)
    print("Compose smoke test passed: upload, durable worker, polling, paginated results, download, and source row alignment.")
