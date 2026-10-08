import asyncio
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.job_models import RowResult, NaicsResolution, ScoreResult
from app.main import create_app
from app.pipeline import Pipeline
from test_jobs import setup, submit, xlsx, FakeScorer


def test_results_pagination_filters_and_legacy_records(setup):
    settings, repo, store = setup
    with TestClient(create_app(settings=settings)) as client:
        job_id = submit(client, xlsx([[" Alpha ", "541330", 123]], headers=["Business Name", "NAICS", "ZIP"])).json()["job_id"]
        assert client.get(f"/api/v1/jobs/{job_id}/rows").status_code == 409
        asyncio.run(Pipeline(repo, store, settings).process(repo.claim()))
        normalized = client.get(f"/api/v1/jobs/{job_id}/rows").json()["rows"][0]
        assert normalized["canonical_account"]["business_name"] == "Alpha"
        assert normalized["canonical_account"]["postal_code"] == "00123"
        assert normalized["naics"]["status"] == "unverified"
        assert "NAICS_REFERENCE_NOT_CONFIGURED" in normalized["issues"]
        statuses = ["invalid", "scored_with_warnings", "scored", "needs_review"]
        # Insert out of order, including a legacy result with no canonical snapshot.
        repo.save_results(job_id, [RowResult(source_row_number=n, status=status, issues=[],
            naics=NaicsResolution(status="unverified"), scores={"Zero": ScoreResult(value=0, status="scored")})
            for n, status in zip([8, 5, 3, 2], statuses)])
        with repo.connection() as db:
            legacy = json.loads(db.execute("SELECT result FROM batch_job_rows WHERE job_id=? AND source_row_number=2", (job_id,)).fetchone()[0])
            legacy.pop("canonical_account")
            db.execute("UPDATE batch_job_rows SET result=? WHERE job_id=? AND source_row_number=2", (json.dumps(legacy), job_id))
        page = client.get(f"/api/v1/jobs/{job_id}/rows?offset=1&limit=2").json()
        assert (page["offset"], page["limit"], page["total"]) == (1, 2, 4)
        assert [row["source_row_number"] for row in page["rows"]] == [3, 5]
        for status in statuses:
            filtered = client.get(f"/api/v1/jobs/{job_id}/rows?status={status}").json()
            assert filtered["total"] == 1 and filtered["rows"][0]["status"] == status
        first = client.get(f"/api/v1/jobs/{job_id}/rows").json()["rows"][0]
        assert first["canonical_account"] is None and first["scores"]["Zero"]["value"] == 0
        assert client.get(f"/api/v1/jobs/{job_id}/rows?offset=100").json()["rows"] == []
        repo.update(job_id, status="failed")
        assert client.get(f"/api/v1/jobs/{job_id}/rows").status_code == 409


@pytest.mark.parametrize("query", ["offset=-1", "offset=no", "limit=0", "limit=201", "status=unknown"])
def test_results_query_validation(setup, query):
    settings, repo, store = setup
    with TestClient(create_app(settings=settings)) as client:
        result = client.get(f"/api/v1/jobs/{uuid4()}/rows?{query}")
        assert result.status_code == 422 and result.json()["error"]["code"] == "INVALID_REQUEST"


def test_unknown_result_job_and_invalid_uuid(setup):
    settings, repo, store = setup
    with TestClient(create_app(settings=settings)) as client:
        assert client.get(f"/api/v1/jobs/{uuid4()}/rows").status_code == 404
        assert client.get("/api/v1/jobs/not-an-id/rows").status_code == 422


def test_results_partial_scoring_failure(setup):
    settings, repo, store = setup

    class Broken(FakeScorer):
        name, required_fields = "Broken", ()

        def score(self, features):
            raise ValueError("private error")

    class Zero(FakeScorer):
        name, required_fields = "Zero", ()

        def score(self, features):
            return {number: ScoreResult(value=0, status="scored") for number in features}

    with TestClient(create_app(settings=settings)) as client:
        job_id = submit(client, xlsx([["Alpha", "541330", "00123"]])).json()["job_id"]
        asyncio.run(Pipeline(repo, store, settings, scorers=[Broken(), Zero()]).process(repo.claim()))
        row = client.get(f"/api/v1/jobs/{job_id}/rows").json()["rows"][0]
        assert row["status"] == "needs_review"
        assert row["scores"]["Zero"]["value"] == 0
        assert row["scores"]["Broken"]["issues"] == ["MODEL_ERROR"]
        assert "private error" not in json.dumps(row)
