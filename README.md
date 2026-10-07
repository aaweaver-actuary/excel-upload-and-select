# Excel Upload and Select

A React/TypeScript frontend and a FastAPI/Python backend for importing Excel data, reviewing RapidFuzz column suggestions, and processing the complete selected worksheet.

## Start with Docker Compose

Requires Docker with Compose. No local Node or Python installation is needed to run the app.

```sh
docker compose up --build --wait
```

Open **http://localhost:8080**. The Python API documentation is at **http://localhost:8000/docs**. Both published ports are bound to localhost. The frontend waits for the backend health check before starting, and Nginx forwards `/api` requests to Python.

If either port is occupied, copy `.env.example` to `.env` and change `FRONTEND_PORT` or `BACKEND_PORT`. Alternatively, run `BACKEND_PORT=8001 FRONTEND_PORT=8081 docker compose up --build --wait`; then open http://localhost:8081 and use http://localhost:8001/docs. Internal service ports and API proxy paths stay the same. For an alternate frontend port, pass its URL to the smoke test: `python3 scripts/smoke.py http://localhost:8081`.

```sh
docker compose down
```

## Import a workbook

1. Choose an `.xlsx` file. CSV and legacy `.xls` files are intentionally unsupported.
2. Choose a worksheet; the first worksheet is selected initially. **Row 1 must contain headers.** Completely empty data rows are skipped.
3. Review the mappings. Unique normalized exact matches are accepted automatically. Fuzzy suggestions require approval; ambiguous suggestions require choosing a column or explicitly skipping the field. Choosing a column manually confirms that choice.
4. Click **Process data**. Every imported data row is sent to Python, even though previews show only ten rows.

The defaults allow **50,000 data rows**, a **20 MiB workbook**, and a **64 MiB JSON request**. A workbook under the file limit can still exceed the JSON limit after decompression. Processing is synchronous, and workbook parsing happens in the browser.

Blank and duplicate headers retain their original Excel column IDs (`A`, `B`, `C`, …), so they cannot overwrite each other or shift values into the wrong column. A source column can only map to one destination field. All six default fields are optional, but at least one must be mapped.

Cell values preserve strings, finite numbers, booleans, and nulls. Dates become ISO strings; rich text and hyperlinks use their visible text. Formula cells use their saved, cached result. Formulas without a cached result and Excel error cells are rejected with a cell address; recalculate and save the workbook in Excel before retrying. Numeric display formatting is not applied, so store identifiers requiring leading zeros as text.

Python maps each row, trims surrounding text whitespace, converts empty text to null, and returns row counts, mapped/unmapped fields, nonempty counts per field, and a ten-row processed preview. It preserves row order and does not deduplicate or discard rows after mapping. Imported data is held in memory during processing and is not persisted.

## Change the column definitions

**The single source of truth is [`backend/app/columns.py`](backend/app/columns.py).** Edit `FIELDS` there; the frontend obtains its controls from `GET /api/schema`, so adding or renaming a field requires no corresponding TypeScript field list.

```python
FIELDS = (
    Field("firstName", "First Name", ("given name", "fname")),
    Field("email", "Email", ("e-mail", "email address"), required=True),
    Field("customerId", "Customer ID", ("customer number", "client id")),
)
```

- `key`: the destination key used in processed rows.
- `label`: the displayed name; also used for matching.
- `aliases`: other known header names that qualify as exact matches after normalization.
- `required`: requires a column mapping; it does not require a nonempty value in every row.

Matching normalizes Unicode, case, punctuation, underscores, and whitespace. Non-exact names are compared against the key, label, and aliases with RapidFuzz `WRatio`. Scores are similarity scores, **not probabilities**. Suggestions default to a score of at least 80, with up to three ranked candidates per field. Unique exact matches take precedence; equal best scores and competing mappings are ambiguous. Every non-exact selected mapping must be confirmed, regardless of its score. Python independently enforces these rules when processing.

Edit `Settings` in the same file to change thresholds, preview length, and limits. If changing `max_request_bytes`, also update `client_max_body_size` in `nginx.conf`. Rebuild the backend and refresh the browser after configuration changes:

```sh
docker compose up --build --wait
```

## Add business processing

Replace or extend `process_rows` in [`backend/app/processing.py`](backend/app/processing.py). Keep `validate_import` at the start so invalid or unapproved mappings are rejected. The default implementation processes every source row and returns a bounded preview; add your transformations or downstream integration here.

## Develop locally

Requires Node **24** (or 26+) and Python **3.13+**. From the project root:

```sh
npm ci
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-test.lock
```

Run Python in one terminal:

```sh
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Run the frontend in another terminal:

```sh
npm run dev
```

Open the Vite URL printed in the terminal, normally http://localhost:5173. Vite proxies `/api` to localhost:8000, so the browser uses the same API paths in local development and Compose.

`package-lock.json` locks frontend dependencies. Python production and test dependencies are pinned in `backend/requirements.lock` and `backend/requirements-test.lock`; their direct dependency definitions are in `backend/pyproject.toml`. To refresh Python locks with `uv`:

```sh
uv pip compile backend/pyproject.toml --python 3.13 -o backend/requirements.lock
uv pip compile backend/pyproject.toml --extra test --python 3.13 -o backend/requirements-test.lock
```

## Test and verify

Local checks:

```sh
npm run typecheck
npm run test:coverage
npm run build
cd backend
../.venv/bin/python -m pytest
```

Run the same coverage suites entirely inside Docker:

```sh
docker compose --profile test run --build --rm frontend-test
docker compose --profile test run --build --rm backend-test
```

Frontend coverage must reach **100% statements, branches, functions, and lines**. Python coverage must reach **100% lines and branches**. Tests, test helpers, type-only definitions, and frontend bootstrap code are excluded; all application logic and Python routes are covered. Frontend reports are written to `coverage/`; local backend runs produce `backend/coverage.xml`.

The tests cover real XLSX parsing, multiple worksheets, blank and duplicate headers, cell conversions, full-row submission, approval and skipping, mapping conflicts, required fields, limits, retries, stale requests, actual RapidFuzz scoring, and API validation.

With Compose running, verify the real HTTP flow through Nginx:

```sh
python3 scripts/smoke.py
```

The smoke test checks the frontend, health, schema, suggestions, rejection of unapproved fuzzy mappings, approved processing, and all twelve fixture rows despite the ten-row preview. It uses only Python's standard library. GitHub Actions runs type checks, coverage suites, the frontend build, and this Compose smoke test.

## API shape

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health status. |
| `GET /api/schema` | Field definitions and settings. |
| `POST /api/match-columns` | Suggestions for `{columns: [{id, label}]}`. |
| `POST /api/process` | Process `{columns, rows, mapping, confirmedFields}`. |

Rows are keyed by **source column ID**, while mappings are keyed by **destination field key**:

```json
{
  "columns": [{"id": "A", "label": "Emial"}],
  "rows": [{"A": " person@example.com "}],
  "mapping": {"email": "A"},
  "confirmedFields": ["email"]
}
```

Invalid requests return HTTP 422; oversized request bodies return HTTP 413. The interactive API documentation provides request schemas. `confirmedFields` records deliberate approvals, manual choices, or explicit skips of ambiguous fields; it is a workflow acknowledgement rather than an authentication mechanism.
