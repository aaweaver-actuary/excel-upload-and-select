# Excel Upload and Select

A React/TypeScript mapping interface and a FastAPI/Python batch backend. Upload an Excel workbook, approve column mappings, poll a durable job, and download the original worksheet data with processing results appended.

## Start with Docker Compose

```sh
docker compose up --build --wait
```

Open **http://localhost:8080**; API documentation is at **http://localhost:8000/docs**. Both ports bind to localhost. Nginx forwards `/api` to FastAPI. Copy `.env.example` to `.env` to configure limits and alternate ports.

Compose runs the frontend, API, and a separate Python worker. SQLite and job artifacts share the **job-data** volume at `/data/jobs`. Stopping containers with `docker compose down` preserves accepted jobs; removing the volume deletes the database and workbooks.

## Import a workbook

1. Choose an `.xlsx` file and worksheet. Row 1 contains headers.
2. Map Business Name and any optional account/address/NAICS fields. Exact matches are accepted automatically; approve fuzzy mappings or choose a source column explicitly.
3. Click **Process data**. The browser uploads the original file with mapping metadata; Python independently validates it before accepting a job.
4. Poll status and download the result workbook when processing completes.

The backend preserves rows 2 through the last row containing a source value, including interior empty rows. Blank rows and rows without a usable business name are invalid individually. Trailing formatting-only rows are ignored. Physical Excel row numbers are durable identifiers. Blank and duplicate headers use column-letter IDs, so source values cannot overwrite one another.

The results worksheet preserves source values and order, then appends Source Row Number, Processing Status, issue codes/descriptions, NAICS submitted/final/provenance fields, and configured score outputs. A Run Summary records counts, processing versions, timestamp, and mapping. Other input worksheets and complex formatting are not reproduced.

Formula cells use saved cached results. Uncached formulas and Excel errors produce row diagnostics and are preserved as literal text; formulas and macros are never evaluated. Store identifiers with significant leading zeros as text. Canonical postal codes can be normalized separately without changing the submitted value.

**This is a backend foundation:** no real vendor, authoritative NAICS dataset, or business scorer is configured. Valid rows therefore return `needs_review` with `SCORING_NOT_CONFIGURED`, rather than fabricated scores. Syntactically plausible submitted NAICS codes are explicitly `unverified` until an approved reference set is injected. Fake providers and scorers run only in tests.

## Architecture and extension points

The original project had a synchronous JSON preview API, React/ExcelJS parsing, RapidFuzz column matching, and Docker Compose with no database, worker, migrations, or storage. The foundation keeps FastAPI, matching, the settings dataclass, locked dependencies, Nginx, and existing testing conventions. It adds standard-library SQLite repositories, an atomic local artifact store, openpyxl, multipart uploads, and one worker service. No Redis, queue service, ORM, or dataframe library is introduced.

- `backend/app/accounts.py` defines the canonical account schema and derives mapping fields. Business Name is required; NAICS and other fields are optional. `columns.py` retains matching/settings and the old contact schema for the legacy synchronous endpoint.
- `workbooks.py` owns ingestion, independent mapping validation, canonical construction, source alignment checks, and XLSX output.
- `pipeline.py` executes ingestion → validation → enrichment → reference lookup/features → scoring → output. Raw workbook data, canonical accounts, and results remain distinct.
- `enrichment.py` defines provider-owned identities/results and NAICS resolution. Implement an approved vendor adapter behind `NaicsProvider`; convert transient failures into `ProviderFailure` with retryability and optional Retry-After seconds. The resolver supplies explicit deadlines, finite retries with jitter, bounded concurrency, within-job deduplication, cross-job TTL caching, and durable provenance. Authentication/not-found/ambiguous outcomes must not be retried as transient failures.
- Inject an approved full code set and version through `NaicsReference`. Reference memberships are never inferred from six-digit syntax alone. Provider/configuration and reference versions participate in cache keys.
- `scoring.py` provides reference lookup, feature construction, and independent batch scorers. Each scorer declares name/version/required fields and returns results keyed by source row number. Malformed outputs and exceptions are contained; another scorer can still succeed. No model logic belongs in routes or Excel.

Wire approved dependencies through the worker's `Pipeline` construction. Record configuration changes through provider/reference/scorer versions and set `PIPELINE_VERSION` to the deployment's build identifier. Recovery refuses to mix processing versions within an interrupted job.

## Durable processing and recovery

SQLite uses WAL, foreign keys, bounded lock waits, and a versioned schema (`PRAGMA user_version`, currently 1). Startup creates the schema idempotently and rejects newer unsupported versions. Future schema changes require a new migration version.

A worker holds an exclusive OS file lock for its lifetime. Additional workers wait; one active worker claims queued jobs transactionally. External enrichment is concurrent within a job. Use a **single host with a local filesystem**; network shares and multi-host worker scaling are unsupported.

A restart recovers interrupted jobs and retains saved enrichment. Deterministic stages may rerun. Successful provider results are checkpointed before scoring/output, and progress updates are chunked. Systemic failures retry up to `WORKER_MAX_ATTEMPTS`; fatal workbook failures terminate the job. Row-level problems produce results rather than failing the batch. Failed jobs can be resubmitted through the upload flow.

Inputs are stored by generated job ID, never by user filenames. Files are written through temporary artifacts and atomic replacement. A job becomes completed only after its result workbook is saved. The DB stores job metadata, row diagnostics/enrichment/scores, and enrichment cache records; the immutable input remains the raw-data source.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /api/health` | Existing liveness convention. |
| `GET /api/ready` | Database, writable artifact volume, and recent active-worker heartbeat; 503 when unavailable. |
| `GET /api/schema` | Canonical mapping fields and public import settings. |
| `POST /api/match-columns` | Existing `{columns: [{id, label}]}` suggestion contract for canonical fields. |
| `POST /api/v1/jobs` | Multipart `file` plus JSON string `metadata`; returns 202 and job ID. |
| `GET /api/v1/jobs/{id}` | Status, stage, counters, timestamps, versions, metrics, and sanitized fatal error. |
| `GET /api/v1/jobs/{id}/result` | XLSX for completed jobs; 409 when not ready/failed, 404 when unknown. |
| `POST /api/process` | Retained synchronous JSON contact-preview contract; no persistence or batch enrichment. |

Job metadata retains the frontend's destination-to-source mapping direction:

```json
{
  "sheet_name": "Accounts",
  "mapping": {
    "business_name": "A",
    "address_line_1": "B",
    "postal_code": "C",
    "naics": "D"
  },
  "confirmedFields": []
}
```

Omit optional NAICS mapping when absent. Non-exact mappings require deliberate confirmation; duplicate JSON keys, reused source columns, nonexistent sources, unknown canonical fields, and missing business-name mapping are rejected before acceptance. New job routes use stable `{"error":{"code":"...","message":"..."}}` envelopes. Internal exception payloads are not exposed.

Public job statuses are `queued`, `running`, `completed`, `completed_with_issues`, and `failed`; the stage is separate. Row statuses are `scored`, `scored_with_warnings`, `needs_review`, and `invalid`.

## Configuration, privacy, and operations

Environment settings are parsed centrally by the existing `Settings` dataclass and shared between API/worker in Compose. Defaults are a **20 MiB upload**, **64 MiB request**, **50,000 rows**, **200 MiB expanded workbook**, and **1,000,000 parsed cells**. Set `MAX_ROWS=5000` for an operational 5,000-row cap. If changing request limits, also align Nginx's `client_max_body_size`.

Worker polling defaults to one second; UI polling defaults to two seconds. Enrichment defaults are eight concurrent requests, a ten-second deadline per attempt, two retries, and a one-day cache TTL. Provider-requested waits exceeding the deadline budget are reported as failures rather than retried early.

`ARTIFACT_RETENTION_DAYS=0` disables automatic deletion until an organizational retention period is supplied. A positive value deletes finished jobs and their artifacts after the configured period during idle worker maintenance. Back up the job-data volume with a consistent SQLite backup/snapshot procedure.

Worker logs are structured JSON with job ID/stage and safe provider timing/outcome metadata. They omit names, addresses, rows, vendor payloads, and credentials. Per-job API metrics include stage/job duration, provider requests/attempts/errors/rate limiting/cache hits, and row outcome counts. Together these support straight-through-processing and manual-review rate calculations.

No authentication system existed in the original project. Compose ports remain localhost-bound; deploy within an approved internal access boundary and supply an organizational authentication policy before exposing insured data beyond that boundary.

## Develop and verify

Requires Node 24 (or 26+) and Python 3.13+:

```sh
npm ci
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-test.lock
```

Run API and worker in separate terminals from `backend/` with the same `JOB_ARTIFACT_DIRECTORY` (default `.cache/jobs` relative to the working directory):

```sh
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
../.venv/bin/python -m app.worker
```

Run `npm run dev` from the project root. Vite proxies `/api` to port 8000.

```sh
npm run typecheck
npm run test:coverage
npm run build
cd backend
../.venv/bin/python -m pytest
```

Both application suites retain 100% coverage thresholds. Tests use real XLSX parsing/output, actual SQLite and filesystem storage, fake providers/scorers, the six-row acceptance scenario, and a 5,000-row alignment scenario with distinct scores. They cover provider deadlines/retries, deduplication, cache expiry, partial scoring, worker exclusion/recovery, retention, invalid workbook/mapping/error contracts, and asynchronous UI polling/stale responses. No live vendor is called.

```sh
docker compose --profile test run --build --rm frontend-test
docker compose --profile test run --build --rm backend-test
python3 scripts/smoke.py
```

The standard-library smoke test exercises upload → durable worker → polling → download through Nginx and verifies submitted values, row count, row identifiers, and honest unconfigured-scoring statuses. GitHub Actions continues to run the local coverage/build checks and Compose smoke test.

Dependency definitions live in `backend/pyproject.toml`; refresh both locks with `uv pip compile` as before. See [foundation PR notes](docs/backend-foundation-pr.md) for a review-ready change description.
