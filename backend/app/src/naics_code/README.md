# Neural Metrics client

`NmClient` and `AsyncNmClient` reuse one NM session token and one HTTP connection
pool per instance. Authentication happens on the first lookup. Reuse a client
for the workload and close it with a context manager. These clients are
independent of the workbook worker.

## Response extraction

The request/session Pydantic models follow the original draft. The company
response schema is not available yet, so an extractor is required. It receives
`(decoded_json, submission)` and synchronously returns a `NmClassification`. Use the exact
vendor Pydantic response model inside your extractor once supplied, then map its
outcome to one of these client classifications:

```python
from app.src.naics_code import NmClassification

found = NmClassification(status="found", naics="541330")
completed_miss = NmClassification(status="not_found")
still_processing = NmClassification(status="pending")
```

These are normalized outcomes, not an assumed NM JSON schema. Codes must be
six-digit strings; convert numeric vendor codes in the extractor. Format checks
do not establish authoritative NAICS membership. The exact `submission` is
provided so the extractor can match the company within a vendor response.

Raise an exception for a malformed or unrecognized response. JSON decoding,
extractor exceptions, and invalid classifications become `error` results with
`NM_INVALID_RESPONSE`. Unrecognized or pending responses are never inferred to
be completed misses. The examples below import your adapter as `extract_nm`.

## Synchronous calls

```python
from app.src.naics_code import NmClient, Submission
from your_nm_adapter import extract_nm

with NmClient(extract_nm) as client:
    result = client.lookup("Acme", "1 Main St")
    print(result.status, result.returns_naics, result.naics)

    for result in client.iter_lookup([
        Submission(name="Acme", address="1 Main St", id="source-row-2"),
        Submission(name="Other", address="2 Main St", id="source-row-3"),
    ]):
        print(result.input_index, result.submission.id, result.status)
```

`lookup(name, address, **options)` also accepts `country` (default `"US"`), `id`,
`lean_crawling`, `force_recrawl`, `force_content_cache_refresh`, `lro_submission`,
and `property_details` (all flags default to `False`).
`lookup_submission(submission)` accepts an already validated `Submission`.

An omitted ID is a deterministic hash of name, address, and country. Iterators
also return a zero-based `input_index`, distinguishing identical businesses.
Duplicate inputs each receive a result; no calls are deduplicated.

## Concurrent async calls

```python
import asyncio
from contextlib import aclosing
from app.src.naics_code import AsyncNmClient, Submission
from your_nm_adapter import extract_nm

async def classify(submissions):
    async with AsyncNmClient(extract_nm) as client:
        result = await client.lookup("Acme", "1 Main St")
        print(result.status, result.returns_naics)

        async with aclosing(client.iter_lookup(submissions, concurrency=8)) as results:
            async for result in results:
                # Handle each completed request here immediately.
                print(result.input_index, result.status, result.naics)

asyncio.run(classify([
    Submission(name="Acme", address="1 Main St"),
    Submission(name="Other", address="2 Main St"),
]))
```

The iterator keeps at most `concurrency` lookup tasks alive (default `8`) and
emits results in completion order. Slow requests do not hold up other results
or prevent new work from starting. Simultaneous completions may appear in either
order. This limit applies to that iterator; separately started lookups/iterators
have their own workloads. The synchronous iterator is sequential.

Use `aclosing` when stopping early. Explicit iterator closure or cancellation
cancels and awaits outstanding tasks. Use an async client within one event loop.

## Outcome handling

| `status` | `returns_naics` | Meaning |
| --- | --- | --- |
| `found` | `True` | The extractor returned a six-digit code. |
| `not_found` | `False` | NM completed without a code. |
| `pending` | `False` | NM is still processing; this client does not poll. |
| `error` | `False` | The request or response interpretation failed. |

Check `status == "not_found"` when choosing a next step after a completed miss.
`returns_naics == False` also includes pending and failed requests. The client
never invokes another provider.

Error codes are `NM_AUTH_ERROR` (401/403), `NM_RATE_LIMIT` (429), `NM_HTTP_ERROR`
(other unsuccessful HTTP responses), `NM_TIMEOUT`, `NM_TRANSPORT_ERROR`, and
`NM_INVALID_RESPONSE`. Invalid credentials/submission fields and use of a closed
client raise exceptions as configuration or programming errors.

A submission HTTP 401 triggers one session refresh and one replay of the same
payload. Concurrent rejected requests share the refreshed session, even when NM
renews the same token value. Other failures have no automatic retries of
potentially billable submissions. The default timeout is 10 seconds per HTTP
request; pass `timeout=...` to either client to change it.

## Configuration

`NmApiDetails()` reads `NEURALMETRICS_API_KEY` and optional `PEM_PATH` when
constructed. No `.env` file is loaded automatically. `PEM_PATH` is a certificate
verification bundle, as in the draft; omit it to use HTTPX's standard trust
store. Explicit configuration is supported:

```python
from pathlib import Path
from app.src.naics_code import NmApiDetails, NmClient

details = NmApiDetails(key=your_api_key, pem_path=Path("company-ca.pem"))
with NmClient(extract_nm, api_details=details, timeout=15) as client:
    result = client.lookup("Acme", "1 Main St")
```

## NAICS context

```python
from app.src.naics_code import NaicsCodeContext

context = NaicsCodeContext(name="Acme", address="1 Main St")
context.apply_nm_result(result)
print(context.naics_code, context.naics4_code, context.is_missing())

# Record a result from a future independently invoked R6 implementation:
context.apply_r6_result("541330")
context.agent_entered_code = "541310"
```

Code preference is agent-entered → NM → R6. Missing codes and their two/four-digit
derivatives are `None`. Missing descriptions are `"Unknown"`; the existing
description helpers remain placeholders. Properties never call APIs. Applying
an NM result for a different name/address raises `ValueError`. Every NM outcome
is retained in `context.nm_result`. The unimplemented R6 function raises
`NotImplementedError` instead of returning a fabricated code.

`NmLookupResult` serializes `returns_naics`. To save a representation that can
be validated back into this Pydantic model, use
`result.model_dump(round_trip=True)` to omit computed fields.
