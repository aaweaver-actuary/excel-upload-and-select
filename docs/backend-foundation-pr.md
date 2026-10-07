# Durable workbook enrichment and scoring foundation

The previous workflow parsed Excel in the browser, synchronously sent all rows to FastAPI, and returned a ten-row preview. Accepted data was not durable, and there was no result workbook. This change uploads the original workbook into a persisted asynchronous job, processes it in a separate Python worker, and returns every selected source row with auditable processing metadata appended.

## Existing components and architecture choice

The repository already supplied React/ExcelJS, RapidFuzz mapping suggestions and approvals, FastAPI/Pydantic, a settings dataclass, locked Python dependencies, Nginx, Docker Compose, pytest/Vitest coverage gates, and a Compose smoke test. It had no database, ORM, migrations, queue, background worker, or artifact storage. These conventions are reused. SQLite on a local shared volume and one active worker were selected for the initial single-host deployment; no Redis, ORM, dataframe library, or additional database service is added.

## Resulting behavior

- Versioned multipart job creation validates workbook limits and approved column-letter mappings before returning 202. Business name is required; NAICS is optional.
- Raw values, canonical accounts, and row results remain separate. Backend-generated physical row numbers preserve source alignment, including interior blank rows, duplicate headers, and missing identity values.
- Transactional job claiming, exclusive worker ownership, row checkpoints, atomic artifacts, bounded retries, and version checks support recovery without repeating successful enrichment unnecessarily.
- NAICS resolution supplies provider abstractions, provenance, normalization/reference validation boundaries, deduplication, configurable caching/concurrency/deadlines, and explicit provider failures. Batch scorers operate independently on canonical features.
- The frontend uploads the file, polls status, and downloads the result. Output includes submitted columns, row status/issues, NAICS provenance, configured scores, and a Run Summary.

## Validation

Verified frontend typecheck, coverage, and production build; backend pytest locally and in the Linux Docker image; and the complete Compose smoke test through Nginx. The 121 backend tests and 55 frontend tests pass with 100% application coverage; coverage thresholds are unchanged. Integration tests use real XLSX fixtures, actual SQLite repositories and artifact storage, fake providers/scorers, the six-row acceptance case, and 5,000 rows with distinct scores to detect alignment errors. Additional tests cover bounded provider failures, cache expiry, partial scoring, worker exclusion/recovery, retention, malformed workbooks, and stale UI polling. CI requires no third-party enrichment service.

## Deployment and remaining integrations

Compose adds a Python worker and the persistent job-data volume. The deployment is single-host/local-filesystem; only one worker is active. Retention defaults to disabled until an organizational period is supplied. API ports remain localhost-bound.

No approved vendor API, authoritative NAICS dataset, reference tables, or business scoring rules existed in the repository. They remain explicit injectable extension points. Production outputs never fabricate scores: usable rows return needs_review with SCORING_NOT_CONFIGURED, and syntactically plausible NAICS codes are explicitly unverified until a reference set is configured.
