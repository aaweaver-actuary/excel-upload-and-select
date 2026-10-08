"""SQLite repositories and atomic local artifacts for a single-host deployment."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Protocol

from .job_models import ApplicationError, RowResult


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class ArtifactStore(Protocol):
    def save_input(self, job_id: str, data: bytes) -> str: ...
    def open_input(self, job_id: str) -> bytes: ...
    def save_output(self, job_id: str, data: bytes) -> str: ...
    def output_path(self, job_id: str) -> Path: ...


class LocalArtifactStore:
    def __init__(self, root: Path):
        self.root = root / "artifacts"

    def _save(self, job_id, name, data):
        directory = self.root / job_id
        try:
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / name
            temporary = directory / (name + ".tmp")
            with temporary.open("wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(target)
            return str(target)
        except OSError as error:
            raise ApplicationError("ARTIFACT_STORAGE_ERROR", "Unable to store the job artifact.", 503) from error

    def save_input(self, job_id, data):
        return self._save(job_id, "input.xlsx", data)

    def open_input(self, job_id):
        return (self.root / job_id / "input.xlsx").read_bytes()

    def save_output(self, job_id, data):
        return self._save(job_id, "result.xlsx", data)

    def output_path(self, job_id):
        return self.root / job_id / "result.xlsx"

    def remove(self, job_id):
        shutil.rmtree(self.root / job_id, ignore_errors=True)


class JobRepository:
    def __init__(self, root: Path):
        self.root = root
        self.database = root / "jobs.sqlite3"

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise RuntimeError("Database schema is newer than this application.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL, stage TEXT,
                    original_filename TEXT NOT NULL, input_artifact_uri TEXT NOT NULL,
                    output_artifact_uri TEXT, metadata TEXT NOT NULL, total_rows INTEGER NOT NULL,
                    processed_rows INTEGER NOT NULL DEFAULT 0, scored_rows INTEGER NOT NULL DEFAULT 0,
                    needs_review_rows INTEGER NOT NULL DEFAULT 0, invalid_rows INTEGER NOT NULL DEFAULT 0,
                    versions TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0, error_code TEXT, error_message TEXT,
                    metrics TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS pending_jobs ON batch_jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS batch_job_rows (
                    job_id TEXT NOT NULL REFERENCES batch_jobs(id) ON DELETE CASCADE,
                    source_row_number INTEGER NOT NULL, enrichment TEXT, result TEXT, updated_at TEXT NOT NULL,
                    PRIMARY KEY(job_id, source_row_number)
                );
                CREATE TABLE IF NOT EXISTS enrichment_cache (
                    key TEXT PRIMARY KEY, result TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS worker_health (id INTEGER PRIMARY KEY CHECK(id=1), heartbeat REAL NOT NULL);
                PRAGMA user_version=1;
            """)

    def create(self, job_id, filename, input_uri, metadata, total_rows, versions):
        with self.connection() as db:
            db.execute("""INSERT INTO batch_jobs
                (id,status,original_filename,input_artifact_uri,metadata,total_rows,versions,created_at)
                VALUES (?,'queued',?,?,?,?,?,?)""",
                (job_id, filename, input_uri, metadata.model_dump_json(), total_rows, json.dumps(versions), timestamp()))
        return self.get(job_id)

    def get(self, job_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM batch_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise ApplicationError("JOB_NOT_FOUND", "The job does not exist.", 404)
        job = dict(row)
        for field in ("metadata", "versions", "metrics"):
            job[field] = json.loads(job[field])
        return job

    def claim(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT id FROM batch_jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return None
            job_id = row["id"]
            db.execute("""UPDATE batch_jobs SET status='running', stage='ingestion',
                       started_at=COALESCE(started_at,?), attempts=attempts+1 WHERE id=?""", (timestamp(), job_id))
        return self.get(job_id)

    def recover(self, max_attempts):
        # Only the owner of the exclusive worker lock may call recovery.
        with self.connection() as db:
            db.execute("""UPDATE batch_jobs SET status='failed', finished_at=?, error_code='WORKER_RETRIES_EXHAUSTED',
                error_message='Processing could not complete after bounded retries.'
                WHERE status='running' AND attempts>=?""", (timestamp(), max_attempts))
            db.execute("UPDATE batch_jobs SET status='queued' WHERE status='running'")

    def update(self, job_id, **changes):
        allowed = {"status", "stage", "processed_rows", "scored_rows", "needs_review_rows", "invalid_rows",
                   "finished_at", "output_artifact_uri", "error_code", "error_message", "metrics", "versions"}
        if not changes or set(changes) - allowed:
            raise ValueError("Invalid job update.")
        values = [json.dumps(value) if key in {"metrics", "versions"} else value for key, value in changes.items()]
        with self.connection() as db:
            db.execute(f"UPDATE batch_jobs SET {','.join(key+'=?' for key in changes)} WHERE id=?", (*values, job_id))

    def save_enrichment(self, job_id, number, resolution):
        self.save_enrichments(job_id, {number: resolution})

    def save_enrichments(self, job_id, resolutions):
        with self.connection() as db:
            db.executemany("""INSERT INTO batch_job_rows(job_id,source_row_number,enrichment,updated_at) VALUES (?,?,?,?)
                ON CONFLICT(job_id,source_row_number) DO UPDATE SET enrichment=excluded.enrichment,updated_at=excluded.updated_at""",
                [(job_id, number, resolution.model_dump_json(), timestamp()) for number, resolution in resolutions.items()])

    def enrichments(self, job_id):
        with self.connection() as db:
            return {row["source_row_number"]: json.loads(row["enrichment"]) for row in db.execute(
                "SELECT source_row_number,enrichment FROM batch_job_rows WHERE job_id=? AND enrichment IS NOT NULL", (job_id,))}

    def save_results(self, job_id, results: list[RowResult]):
        with self.connection() as db:
            db.executemany("""INSERT INTO batch_job_rows(job_id,source_row_number,result,updated_at) VALUES (?,?,?,?)
                ON CONFLICT(job_id,source_row_number) DO UPDATE SET result=excluded.result,updated_at=excluded.updated_at""",
                [(job_id, row.source_row_number, row.model_dump_json(), timestamp()) for row in results])

    def results(self, job_id, offset, limit, status=None):
        query = "FROM batch_job_rows WHERE job_id=? AND result IS NOT NULL"
        values = [job_id]
        if status is not None:
            query += " AND json_extract(result, '$.status')=?"
            values.append(status)
        with self.connection() as db:
            total = db.execute("SELECT COUNT(*) " + query, values).fetchone()[0]
            rows = db.execute("SELECT result " + query + " ORDER BY source_row_number LIMIT ? OFFSET ?",
                              [*values, limit, offset]).fetchall()
        return total, [RowResult.model_validate_json(row["result"]) for row in rows]

    def cache_get(self, key):
        with self.connection() as db:
            row = db.execute("SELECT result FROM enrichment_cache WHERE key=? AND expires_at>?", (key, time.time())).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key, result, ttl):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO enrichment_cache VALUES (?,?,?)", (key, json.dumps(result), time.time() + ttl))

    def heartbeat(self):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO worker_health VALUES (1,?)", (time.time(),))

    def ready(self, stale_seconds):
        with self.connection() as db:
            row = db.execute("SELECT heartbeat FROM worker_health WHERE id=1").fetchone()
        return row is not None and time.time() - row[0] < stale_seconds

    def expired_jobs(self, retention_days):
        cutoff = datetime.fromtimestamp(time.time() - retention_days * 86400, timezone.utc).isoformat()
        with self.connection() as db:
            return [row[0] for row in db.execute("SELECT id FROM batch_jobs WHERE finished_at<?", (cutoff,))]

    def delete(self, job_id):
        with self.connection() as db:
            db.execute("DELETE FROM batch_jobs WHERE id=?", (job_id,))
