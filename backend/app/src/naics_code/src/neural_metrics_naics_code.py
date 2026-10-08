"""Reusable NM connections; response interpretation belongs to the injected extractor."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
import math
import ssl
import threading
from typing import Any, Self

import httpx

from ..models import NmApiDetails, NmClassification, NmLookupResult, NmSessionResponse, Submission

SESSION_ENDPOINT = "https://api.smartratio.neuralmetrics.ai/smb/api/v1/getSession"
SUBMISSION_ENDPOINT = "https://api.smartratio.neuralmetrics.ai/smb/api/v2/company/submit/batch"

ResponseExtractor = Callable[[Any, Submission], NmClassification]


def _client_options(details: NmApiDetails, timeout: float) -> dict[str, Any]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive.")
    verify = ssl.create_default_context(cafile=str(details.pem_path)) if details.pem_path else True
    return {"verify": verify, "timeout": timeout}


def _session_headers(details: NmApiDetails) -> dict[str, str]:
    return {"Authorization": f"Key {details.key.get_secret_value()}", "Content-Type": "application/json"}


def _submission_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Session {token}", "Content-Type": "application/json", "RequestSource": "API"}


def _error_result(submission: Submission, error: Exception) -> NmLookupResult:
    if isinstance(error, httpx.TimeoutException):
        code = "NM_TIMEOUT"
    elif isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        code = "NM_AUTH_ERROR" if status in {401, 403} else "NM_RATE_LIMIT" if status == 429 else "NM_HTTP_ERROR"
    elif isinstance(error, httpx.RequestError):
        code = "NM_TRANSPORT_ERROR"
    else:
        code = "NM_INVALID_RESPONSE"
    return NmLookupResult(submission=submission, status="error", error_code=code)


def _classify(response: httpx.Response, submission: Submission, extractor: ResponseExtractor) -> NmLookupResult:
    try:
        classification = NmClassification.model_validate(extractor(response.json(), submission))
        return NmLookupResult(submission=submission, status=classification.status, naics=classification.naics)
    except Exception:
        # An adapter exception is a response error, never a completed miss.
        return NmLookupResult(submission=submission, status="error", error_code="NM_INVALID_RESPONSE")


class NmClient:
    """Synchronous lookups using one lazy, reusable NM session and HTTP pool."""

    def __init__(self, extractor: ResponseExtractor, *, api_details: NmApiDetails | None = None,
                 timeout: float = 10, transport: httpx.BaseTransport | None = None):
        if not callable(extractor):
            raise TypeError("extractor must be callable.")
        self._extractor = extractor
        self._details = api_details if api_details is not None else NmApiDetails()
        self._client = httpx.Client(**_client_options(self._details, timeout), transport=transport)
        self._token: str | None = None
        self._generation = 0
        self._session_lock = threading.Lock()

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _ensure_open(self) -> None:
        if self._client.is_closed:
            raise RuntimeError("NM client is closed.")

    def _session(self, rejected_generation: int | None = None) -> tuple[str, int]:
        with self._session_lock:
            if self._token is None or rejected_generation == self._generation:
                response = self._client.post(SESSION_ENDPOINT, headers=_session_headers(self._details))
                response.raise_for_status()
                self._token = NmSessionResponse.model_validate(response.json()).session_token
                self._generation += 1
            return self._token, self._generation

    def lookup(self, name: str, address: str = "", **options: Any) -> NmLookupResult:
        """Look up one business; optional keyword arguments are Submission fields."""
        return self.lookup_submission(Submission(name=name, address=address, **options))

    def lookup_submission(self, submission: Submission) -> NmLookupResult:
        """Look up an already validated submission without losing its identity."""
        self._ensure_open()
        try:
            token, generation = self._session()
            response = self._client.post(SUBMISSION_ENDPOINT, headers=_submission_headers(token), json=submission.payload)
            if response.status_code == 401:
                token, _ = self._session(rejected_generation=generation)
                response = self._client.post(SUBMISSION_ENDPOINT, headers=_submission_headers(token), json=submission.payload)
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as error:
            return _error_result(submission, error)
        return _classify(response, submission, self._extractor)

    def iter_lookup(self, submissions: Iterable[Submission]) -> Iterator[NmLookupResult]:
        """Yield one result per input, sequentially, including duplicate businesses."""
        for index, submission in enumerate(submissions):
            yield self.lookup_submission(submission).model_copy(update={"input_index": index})


class AsyncNmClient:
    """Async lookups using one NM session; use an instance within one event loop."""

    def __init__(self, extractor: ResponseExtractor, *, api_details: NmApiDetails | None = None,
                 timeout: float = 10, transport: httpx.AsyncBaseTransport | None = None):
        if not callable(extractor):
            raise TypeError("extractor must be callable.")
        self._extractor = extractor
        self._details = api_details if api_details is not None else NmApiDetails()
        self._client = httpx.AsyncClient(**_client_options(self._details, timeout), transport=transport)
        self._token: str | None = None
        self._generation = 0
        self._session_lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        self._ensure_open()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _ensure_open(self) -> None:
        if self._client.is_closed:
            raise RuntimeError("NM client is closed.")

    async def _session(self, rejected_generation: int | None = None) -> tuple[str, int]:
        async with self._session_lock:
            if self._token is None or rejected_generation == self._generation:
                response = await self._client.post(SESSION_ENDPOINT, headers=_session_headers(self._details))
                response.raise_for_status()
                self._token = NmSessionResponse.model_validate(response.json()).session_token
                self._generation += 1
            return self._token, self._generation

    async def lookup(self, name: str, address: str = "", **options: Any) -> NmLookupResult:
        return await self.lookup_submission(Submission(name=name, address=address, **options))

    async def lookup_submission(self, submission: Submission) -> NmLookupResult:
        self._ensure_open()
        try:
            token, generation = await self._session()
            response = await self._client.post(SUBMISSION_ENDPOINT, headers=_submission_headers(token), json=submission.payload)
            if response.status_code == 401:
                token, _ = await self._session(rejected_generation=generation)
                response = await self._client.post(SUBMISSION_ENDPOINT, headers=_submission_headers(token), json=submission.payload)
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as error:
            return _error_result(submission, error)
        return _classify(response, submission, self._extractor)

    async def iter_lookup(self, submissions: Iterable[Submission], *, concurrency: int = 8) -> AsyncIterator[NmLookupResult]:
        """Yield results as requests finish, keeping at most concurrency tasks alive.

        Close this iterator (or use contextlib.aclosing) when stopping early.
        """
        if isinstance(concurrency, bool) or not isinstance(concurrency, int) or concurrency <= 0:
            raise ValueError("concurrency must be a positive integer.")
        self._ensure_open()
        inputs = iter(enumerate(submissions))
        pending: dict[asyncio.Task[NmLookupResult], int] = {}

        def fill() -> None:
            while len(pending) < concurrency:
                item = next(inputs, None)
                if item is None:
                    break
                index, submission = item
                pending[asyncio.create_task(self.lookup_submission(submission))] = index

        try:
            fill()
            while pending:
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    index = pending.pop(task)
                    result = task.result().model_copy(update={"input_index": index})
                    fill()
                    yield result
        finally:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
