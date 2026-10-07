import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import runpy
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.job_models import ApplicationError, JobMetadata, NaicsResolution
from app.main import create_app
from app.persistence import JobRepository, LocalArtifactStore
from app.pipeline import Pipeline
from app.worker import StructuredFormatter, main, run_worker, worker_lock
from test_jobs import FakeScorer, setup, submit, xlsx


def test_lock_excludes_second_worker_and_releases_after_error(tmp_path):
    with pytest.raises(RuntimeError):
        with worker_lock(tmp_path) as acquired:
            assert acquired
            with worker_lock(tmp_path) as duplicate:
                assert not duplicate
            raise RuntimeError()
    with worker_lock(tmp_path) as acquired:
        assert acquired


def test_transactional_claim_has_one_winner(setup):
    from concurrent.futures import ThreadPoolExecutor
    settings, repo, store = setup
    repo.create("job", "input.xlsx", "input", JobMetadata(sheet_name="Accounts", mapping={"business_name": "A"}), 1, {})
    with ThreadPoolExecutor(2) as pool:
        claims = list(pool.map(lambda _: repo.claim(), range(2)))
    assert sum(claim is not None for claim in claims) == 1


def test_repository_recovery_retention_and_schema_checks(setup):
    settings, repo, store = setup
    metadata = JobMetadata(sheet_name="Accounts", mapping={"business_name": "A"})
    repo.create("job", "input.xlsx", "input", metadata, 1, {})
    repo.save_enrichment("job", 2, NaicsResolution(status="none"))
    repo.claim()
    repo.recover(1)
    assert repo.get("job")["status"] == "failed"
    assert repo.expired_jobs(0) == ["job"]
    repo.delete("job")
    assert repo.claim() is None
    for changes in ({}, {"unknown": 1}):
        with pytest.raises(ValueError, match="update"):
            repo.update("job", **changes)
    with repo.connection() as db:
        db.execute("PRAGMA user_version=2")
    with pytest.raises(RuntimeError, match="newer"):
        repo.initialize()


def test_artifact_errors_and_readiness_failures(setup, monkeypatch):
    settings, repo, store = setup
    with TestClient(create_app(settings=settings)) as client:
        with monkeypatch.context() as patch:
            patch.setattr(Path, "mkdir", lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))
            with pytest.raises(ApplicationError, match="artifact"):
                store.save_input("job", b"bytes")
            assert client.get("/api/ready").status_code == 503
        with monkeypatch.context() as patch:
            patch.setattr(JobRepository, "ready", lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError()))
            assert client.get("/api/ready").status_code == 503


def test_upload_database_failure_does_not_accept_job(setup, monkeypatch):
    settings, repo, store = setup
    with TestClient(create_app(settings=settings)) as client:
        monkeypatch.setattr(JobRepository, "create", lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError()))
        response = submit(client, xlsx([["Alpha", None, "12345"]]))
        assert response.status_code == 503 and response.json()["error"]["code"] == "JOB_PERSISTENCE_ERROR"
        assert list(store.root.iterdir()) == []


def test_duplicate_metadata_and_streamed_job_request_limit(setup):
    settings, repo, store = setup
    with TestClient(create_app(settings=settings)) as client:
        response = client.post("/api/v1/jobs", files={"file": ("input.xlsx", xlsx([["Alpha"]]))},
            data={"metadata": '{"sheet_name":"Accounts","mapping":{"business_name":"A","business_name":"B"}}'})
        assert response.status_code == 422 and "duplicate" in response.json()["error"]["message"]
    with TestClient(create_app(settings=replace(settings, max_request_bytes=10))) as client:
        response = client.post("/api/v1/jobs", content=b"x" * 11)
        assert response.status_code == 413 and response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_duplicate_scorer_names_rejected(setup):
    settings, repo, store = setup
    with pytest.raises(ValueError, match="unique"):
        Pipeline(repo, store, settings, scorers=[FakeScorer(), FakeScorer()])


def test_active_worker_processes_job_and_idle_retention(setup):
    settings, repo, store = setup
    data = xlsx([["Alpha"]], headers=["Business Name"])
    metadata = JobMetadata(sheet_name="Accounts", mapping={"business_name": "A"})
    repo.create("job", "input.xlsx", store.save_input("job", data), metadata, 1, {})

    async def scenario():
        stop = asyncio.Event()

        class StopAfterJob(Pipeline):
            async def process(self, job):
                await super().process(job)
                stop.set()

        await run_worker(settings, stop, StopAfterJob)

    asyncio.run(scenario())
    assert repo.get("job")["status"] == "completed_with_issues"
    # Retention is disabled by default; idle worker leaves finished jobs intact.
    async def idle(retention):
        stop = asyncio.Event()
        task = asyncio.create_task(run_worker(replace(settings, artifact_retention_days=retention), stop))
        await asyncio.sleep(0.03)
        stop.set()
        await task
    asyncio.run(idle(0))
    assert store.output_path("job").exists()
    repo.update("job", finished_at="2000-01-01T00:00:00+00:00")
    asyncio.run(idle(1))
    assert repo.claim() is None and not store.output_path("job").exists()


def test_standby_worker_waits_and_stopped_worker_exits(setup):
    settings, repo, store = setup

    async def scenario():
        stop = asyncio.Event()
        with worker_lock(repo.root):
            task = asyncio.create_task(run_worker(settings, stop))
            await asyncio.sleep(0.03)
            stop.set()
            await task
        stopped = asyncio.Event()
        stopped.set()
        await run_worker(settings, stopped)
    asyncio.run(scenario())


def test_formatter_emits_only_allowed_fields():
    record = logging.LogRecord("test", logging.INFO, "", 1, "stage_started", (), None)
    record.job_id, record.stage, record.business_name = "job", "output", "confidential"
    result = json.loads(StructuredFormatter().format(record))
    assert result == {"event": "stage_started", "level": "INFO", "job_id": "job", "stage": "output"}


def test_worker_entrypoint_sets_up_signals_and_logs(monkeypatch):
    import app.worker as worker
    captured = []

    async def fake_run_worker(*, stop):
        captured.append(stop)

    monkeypatch.setattr(worker, "run_worker", fake_run_worker)
    asyncio.run(main())
    assert len(captured) == 1
    # Execute the module bootstrap without launching a persistent worker process.
    monkeypatch.setattr(asyncio, "run", lambda coroutine: coroutine.close())
    runpy.run_module("app.worker", run_name="__main__")
