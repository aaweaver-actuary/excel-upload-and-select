import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import aclosing
import importlib
import json
from pathlib import Path
import ssl
import threading

import httpx
from pydantic import BaseModel, ValidationError
import pytest

from app.src.naics_code import (
    AsyncNmClient, NaicsCodeContext, NmApiDetails, NmBatchRequest, NmClassification,
    NmClient, NmLookupResult, NmSessionResponse, Submission,
)
from app.src.naics_code.src import neural_metrics_naics_code as nm
from app.src.naics_code.src.relativity6_naics_code import get_relativity6_naics_code

DETAILS = NmApiDetails(key="test-api-key", pem_path=None)
FOUND = {"status": "found", "naics": "541330"}


def extract(payload, submission):
    # A normalized fixture contract, not an assumption about vendor field names.
    return NmClassification.model_validate(payload)


def handler_for(outcome=FOUND):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url == nm.SESSION_ENDPOINT:
            return httpx.Response(200, json={"sessionToken": "test-session", "metadata": {}})
        return httpx.Response(200, json=outcome)

    return handler, requests


@pytest.fixture(params=["sync", "async"])
def lookup(request):
    def call(handler, *, extractor=extract, **options):
        kwargs = {"api_details": DETAILS, "transport": httpx.MockTransport(handler)}
        if request.param == "sync":
            with NmClient(extractor, **kwargs) as client:
                return client.lookup("Acme", "1 Main St", **options)

        async def run():
            async with AsyncNmClient(extractor, **kwargs) as client:
                return await client.lookup("Acme", "1 Main St", **options)

        return asyncio.run(run())
    return call


def test_models_and_wire_contract():
    submission = Submission(name="Acme", address="1 Main St")
    assert isinstance(submission, BaseModel)
    assert submission.payload == {"companyData": [{
        "companyName": "Acme", "companyAddress": "1 Main St", "country": "US",
        "id": submission.key, "leanCrawling": False, "forceRecrawl": False,
        "forceContentCacheRefresh": False, "lroSubmission": False, "propertyDetails": False,
    }]}
    assert NmBatchRequest(company_data=[submission]).model_dump(by_alias=True) == submission.payload
    assert Submission(name="Acme", address="1 Main St").key == submission.key
    assert Submission(name="AB", address="C").key != Submission(name="A", address="BC").key
    assert Submission(name="Acme", address="1 Main St", country="CA").key != submission.key
    assert Submission(name="Acme", id="row-2").key == "row-2"
    with pytest.raises(ValidationError):
        submission.name = "Changed"


@pytest.mark.parametrize("kwargs", [{"name": " "}, {"name": "Acme", "id": ""},
                                  {"name": "Acme", "property_details": "true"}])
def test_submission_validation(kwargs):
    with pytest.raises(ValidationError):
        Submission(**kwargs)


@pytest.mark.parametrize("payload", [
    {"status": "found"}, {"status": "found", "naics": "12345"},
    {"status": "found", "naics": "541330\n"}, {"status": "found", "naics": 541330},
    {"status": "found", "naics": "abcdef"}, {"status": "not_found", "naics": "541330"},
    {"status": "error"}, {"status": "invented"},
])
def test_classification_validation(payload):
    with pytest.raises(ValidationError):
        NmClassification.model_validate(payload)


def test_result_error_invariants_and_serialization():
    submission = Submission(name="Acme")
    result = NmLookupResult(submission=submission, **FOUND)
    assert result.returns_naics and result.model_dump()["returns_naics"] is True
    assert NmLookupResult.model_validate(result.model_dump(round_trip=True)) == result
    for payload in ({"status": "error"}, {"status": "not_found", "error_code": "NM_TIMEOUT"}):
        with pytest.raises(ValidationError):
            NmLookupResult(submission=submission, **payload)


def test_runtime_environment_and_import_safety(monkeypatch):
    monkeypatch.delenv("NEURALMETRICS_API_KEY", raising=False)
    monkeypatch.delenv("PEM_PATH", raising=False)
    importlib.reload(nm)
    with pytest.raises(ValidationError):
        NmApiDetails()
    monkeypatch.setenv("NEURALMETRICS_API_KEY", "first-key")
    first = NmApiDetails()
    monkeypatch.setenv("NEURALMETRICS_API_KEY", "second-key")
    monkeypatch.setenv("PEM_PATH", "/tmp/nm-cert.pem")
    second = NmApiDetails()
    assert first.key.get_secret_value() == "first-key" and first.pem_path is None
    assert second.key.get_secret_value() == "second-key"
    assert second.pem_path == Path("/tmp/nm-cert.pem")
    assert "second-key" not in repr(second)


@pytest.mark.parametrize("key", ["", " ", "bad\rkey", "bad\nkey"])
def test_invalid_credentials(key):
    with pytest.raises(ValidationError):
        NmApiDetails(key=key)


@pytest.mark.parametrize("token", [None, "", " ", "bad\rvalue", "bad\nvalue", 123])
def test_invalid_session_response(token):
    with pytest.raises(ValidationError):
        NmSessionResponse.model_validate({"sessionToken": token})


@pytest.mark.parametrize("client_type", [NmClient, AsyncNmClient])
def test_configuration_validation_and_certificate(client_type, monkeypatch):
    with pytest.raises(TypeError, match="callable"):
        client_type(None, api_details=DETAILS)
    for timeout in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="positive"):
            client_type(extract, api_details=DETAILS, timeout=timeout)
    context = ssl.create_default_context()
    cafiles = []
    monkeypatch.setattr(nm.ssl, "create_default_context", lambda *, cafile: cafiles.append(cafile) or context)
    client = client_type(extract, api_details=NmApiDetails(key="test", pem_path="/tmp/test.pem"),
                         transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    assert cafiles == ["/tmp/test.pem"]
    if client_type is NmClient:
        client.close()
    else:
        asyncio.run(client.aclose())


def test_defaults_read_environment_at_client_construction(monkeypatch):
    monkeypatch.setenv("NEURALMETRICS_API_KEY", "current-key")
    monkeypatch.delenv("PEM_PATH", raising=False)
    handler, _ = handler_for()
    with NmClient(extract, transport=httpx.MockTransport(handler)) as client:
        assert client.lookup("Acme").returns_naics

    async def run():
        async with AsyncNmClient(extract, transport=httpx.MockTransport(handler)) as client:
            assert (await client.lookup("Acme")).returns_naics
    asyncio.run(run())


@pytest.mark.parametrize("outcome", [FOUND, {"status": "not_found"}, {"status": "pending"}])
def test_outcomes_and_request_contract(lookup, outcome):
    handler, requests = handler_for(outcome)
    seen = []

    def adapter(payload, submission):
        seen.append((payload, submission))
        return extract(payload, submission)

    result = lookup(handler, extractor=adapter, id="row-7", country="CA", lean_crawling=True,
                    force_recrawl=True, force_content_cache_refresh=True, lro_submission=True, property_details=True)
    assert result.status == outcome["status"]
    assert result.returns_naics == (outcome["status"] == "found")
    assert result.error_code is None and result.submission.id == "row-7"
    assert seen == [(outcome, result.submission)]
    assert len(requests) == 2
    assert requests[0].method == requests[1].method == "POST"
    assert requests[0].headers["Authorization"] == "Key test-api-key"
    assert requests[1].headers["Authorization"] == "Session test-session"
    assert requests[1].headers["RequestSource"] == "API"
    assert requests[1].headers["Content-Type"] == "application/json"
    assert all(value == 10 for value in requests[1].extensions["timeout"].values())
    assert json.loads(requests[1].content) == result.submission.payload


@pytest.mark.parametrize("status,code", [(403, "NM_AUTH_ERROR"), (404, "NM_HTTP_ERROR"),
                                        (429, "NM_RATE_LIMIT"), (500, "NM_HTTP_ERROR")])
@pytest.mark.parametrize("phase", ["session", "submission"])
def test_http_errors_do_not_become_misses_or_retry(lookup, status, code, phase):
    requests = []

    def handler(request):
        requests.append(request)
        if phase == "session" or request.url == nm.SUBMISSION_ENDPOINT:
            return httpx.Response(status)
        return httpx.Response(200, json={"sessionToken": "token"})

    result = lookup(handler)
    assert result.status == "error" and not result.returns_naics
    assert result.error_code == code
    assert len(requests) == (1 if phase == "session" else 2)


@pytest.mark.parametrize("phase", ["session", "submission"])
@pytest.mark.parametrize("error,code", [(httpx.ReadTimeout, "NM_TIMEOUT"), (httpx.ConnectError, "NM_TRANSPORT_ERROR")])
def test_transport_errors_are_explicit(lookup, phase, error, code):
    def handler(request):
        if phase == "session" or request.url == nm.SUBMISSION_ENDPOINT:
            raise error("mock failure")
        return httpx.Response(200, json={"sessionToken": "token"})
    result = lookup(handler)
    assert result.status == "error" and result.error_code == code and not result.returns_naics


@pytest.mark.parametrize("phase", ["session", "submission"])
def test_invalid_json(lookup, phase):
    def handler(request):
        if phase == "session" or request.url == nm.SUBMISSION_ENDPOINT:
            return httpx.Response(200, content="not JSON")
        return httpx.Response(200, json={"sessionToken": "token"})
    assert lookup(handler).error_code == "NM_INVALID_RESPONSE"


def test_missing_session_token(lookup):
    assert lookup(lambda request: httpx.Response(200, json={})).error_code == "NM_INVALID_RESPONSE"


@pytest.mark.parametrize("payload", [
    None, {}, {"status": "found", "naics": "bad"}, {"status": "found"},
    NmClassification.model_construct(status="found", naics=None),
    NmClassification(status="found", naics="541330").model_copy(update={"naics": "bad"}),
])
def test_invalid_extractor_outputs(lookup, payload):
    handler, _ = handler_for()
    result = lookup(handler, extractor=lambda raw, submission: payload)
    assert result.status == "error" and result.error_code == "NM_INVALID_RESPONSE"


def test_extractor_exception(lookup):
    def broken(raw, submission):
        raise RuntimeError("adapter failed")
    handler, _ = handler_for()
    assert lookup(handler, extractor=broken).error_code == "NM_INVALID_RESPONSE"


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_context_manager_closes_transport_even_on_error(mode):
    class RecordingTransport(httpx.MockTransport):
        closed = False

        def close(self):
            self.closed = True

        async def aclose(self):
            self.closed = True

    handler, _ = handler_for()
    transport = RecordingTransport(handler)
    if mode == "sync":
        with pytest.raises(RuntimeError, match="caller failed"):
            with NmClient(extract, api_details=DETAILS, transport=transport) as client:
                assert client.lookup("Acme").returns_naics
                raise RuntimeError("caller failed")
    else:
        async def run():
            with pytest.raises(RuntimeError, match="caller failed"):
                async with AsyncNmClient(extract, api_details=DETAILS, transport=transport) as client:
                    assert (await client.lookup("Acme")).returns_naics
                    raise RuntimeError("caller failed")
        asyncio.run(run())
    assert transport.closed


@pytest.mark.parametrize("second_status", [200, 401])
def test_refresh_replays_only_once(lookup, second_status):
    sessions, submissions = [], []

    def handler(request):
        if request.url == nm.SESSION_ENDPOINT:
            sessions.append(request)
            return httpx.Response(200, json={"sessionToken": f"token-{len(sessions)}"})
        submissions.append(request)
        status = 401 if len(submissions) == 1 else second_status
        return httpx.Response(status, json=FOUND)

    result = lookup(handler)
    assert result.status == ("found" if second_status == 200 else "error")
    assert len(sessions) == len(submissions) == 2
    assert submissions[0].headers["Authorization"] == "Session token-1"
    assert submissions[1].headers["Authorization"] == "Session token-2"
    assert submissions[0].content == submissions[1].content


def test_failed_refresh_is_error(lookup):
    sessions = 0

    def handler(request):
        nonlocal sessions
        if request.url == nm.SESSION_ENDPOINT:
            sessions += 1
            return httpx.Response(200, json={"sessionToken": "first"} if sessions == 1 else {})
        return httpx.Response(401)
    result = lookup(handler)
    assert sessions == 2 and result.status == "error" and result.error_code == "NM_INVALID_RESPONSE"


def test_sync_session_reuse_and_duplicate_inputs():
    handler, requests = handler_for()
    submission = Submission(name="Duplicate", address="Address")
    with NmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
        iterator = client.iter_lookup([submission, submission])
        assert not requests
        results = list(iterator)
        assert client.lookup("Other").returns_naics
    assert len([r for r in requests if r.url == nm.SESSION_ENDPOINT]) == 1
    assert [r.input_index for r in results] == [0, 1]
    assert all(r.submission is submission for r in results)
    with pytest.raises(RuntimeError, match="closed"):
        client.lookup("Closed")
    with pytest.raises(RuntimeError, match="closed"):
        with client:
            pass
    client.close()


def test_sync_concurrent_initialization_and_refresh():
    barrier = threading.Barrier(4, timeout=3)
    lock = threading.Lock()
    sessions = 0
    counts = {}

    def handler(request):
        nonlocal sessions
        if request.url == nm.SESSION_ENDPOINT:
            with lock:
                sessions += 1
            # A renewed session may return the same token; generations still matter.
            return httpx.Response(200, json={"sessionToken": "same-token"})
        name = json.loads(request.content)["companyData"][0]["companyName"]
        with lock:
            counts[name] = counts.get(name, 0) + 1
            attempt = counts[name]
        if attempt == 1:
            barrier.wait()
            return httpx.Response(401)
        return httpx.Response(200, json=FOUND)

    with NmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(client.lookup, ["A", "B", "C", "D"]))
    assert sessions == 2 and all(result.returns_naics for result in results)
    assert list(counts.values()) == [2] * 4


def test_async_concurrent_initialization_and_refresh():
    async def run():
        all_rejected = asyncio.Event()
        counts, sessions = {}, 0

        async def handler(request):
            nonlocal sessions
            if request.url == nm.SESSION_ENDPOINT:
                sessions += 1
                await asyncio.sleep(0)
                return httpx.Response(200, json={"sessionToken": "same-token"})
            name = json.loads(request.content)["companyData"][0]["companyName"]
            counts[name] = counts.get(name, 0) + 1
            if counts[name] == 1:
                if len(counts) == 4:
                    all_rejected.set()
                await all_rejected.wait()
                return httpx.Response(401)
            return httpx.Response(200, json=FOUND)

        async with AsyncNmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
            results = await asyncio.gather(*(client.lookup(name) for name in ["A", "B", "C", "D"]))
        assert sessions == 2 and all(result.returns_naics for result in results)
        assert list(counts.values()) == [2] * 4
    asyncio.run(asyncio.wait_for(run(), 3))


def test_async_rolling_stream_preserves_indices_and_does_not_wait_for_slow():
    async def run():
        release_slow = asyncio.Event()
        active, peak, sessions = 0, 0, 0
        consumed = []
        duplicate = Submission(name="Duplicate", address="Address")
        submissions = [Submission(name="Slow"), duplicate, duplicate] + [Submission(name=f"Row {i}") for i in range(12)]

        def inputs():
            for submission in submissions:
                consumed.append(submission)
                yield submission

        async def handler(request):
            nonlocal active, peak, sessions
            if request.url == nm.SESSION_ENDPOINT:
                sessions += 1
                await asyncio.sleep(0)
                return httpx.Response(200, json={"sessionToken": "token"})
            active += 1
            peak = max(peak, active)
            try:
                name = json.loads(request.content)["companyData"][0]["companyName"]
                if name == "Slow":
                    await release_slow.wait()
                else:
                    await asyncio.sleep(0)
                return httpx.Response(200, json=FOUND)
            finally:
                active -= 1

        async with AsyncNmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
            stream = client.iter_lookup(inputs(), concurrency=3)
            assert not consumed and sessions == 0
            early = [await anext(stream) for _ in range(3)]
            assert all(r.input_index != 0 for r in early)
            assert any(r.input_index >= 3 for r in early)
            assert len(consumed) < len(submissions)
            release_slow.set()
            results = early + [r async for r in stream]
            assert (await client.lookup("Extra")).returns_naics
        assert sorted(r.input_index for r in results) == list(range(len(submissions)))
        assert all(r.submission is submissions[r.input_index] for r in results)
        assert peak <= 3 and active == 0 and sessions == 1
        with pytest.raises(RuntimeError, match="closed"):
            await client.lookup("Closed")
        with pytest.raises(RuntimeError, match="closed"):
            async with client:
                pass
        await client.aclose()
    asyncio.run(asyncio.wait_for(run(), 3))


@pytest.mark.parametrize("stop", ["close", "cancel"])
def test_async_stream_cleanup(stop):
    async def run():
        blocked, unblock = asyncio.Event(), asyncio.Event()
        entered, cancelled = set(), set()

        async def handler(request):
            if request.url == nm.SESSION_ENDPOINT:
                return httpx.Response(200, json={"sessionToken": "token"})
            name = json.loads(request.content)["companyData"][0]["companyName"]
            if name == "Fast":
                return httpx.Response(200, json=FOUND)
            entered.add(name)
            if len(entered) == 2:
                blocked.set()
            try:
                await unblock.wait()
                return httpx.Response(200, json=FOUND)
            except asyncio.CancelledError:
                cancelled.add(name)
                raise

        async with AsyncNmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
            names = ["Fast", "A", "B"] if stop == "close" else ["A", "B"]
            stream = client.iter_lookup([Submission(name=name) for name in names], concurrency=3)
            if stop == "close":
                async with aclosing(stream):
                    assert (await anext(stream)).returns_naics
                    await blocked.wait()
            else:
                task = asyncio.create_task(anext(stream))
                await blocked.wait()
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            assert cancelled == entered and len(cancelled) == 2
            assert (await client.lookup("Fast")).returns_naics
            assert asyncio.all_tasks() == {asyncio.current_task()}
    asyncio.run(asyncio.wait_for(run(), 3))


def test_async_input_failure_cleans_up_tasks():
    async def run():
        def inputs():
            yield Submission(name="One")
            raise RuntimeError("input failed")

        handler, _ = handler_for()
        async with AsyncNmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(RuntimeError, match="input failed"):
                await anext(client.iter_lookup(inputs()))
            assert asyncio.all_tasks() == {asyncio.current_task()}
    asyncio.run(run())


@pytest.mark.parametrize("concurrency", [0, -1, True, 1.5])
def test_async_invalid_concurrency(concurrency):
    async def run():
        handler, requests = handler_for()
        async with AsyncNmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ValueError, match="positive integer"):
                await anext(client.iter_lookup([], concurrency=concurrency))
        assert not requests
    asyncio.run(run())


def test_async_empty_stream():
    async def run():
        handler, requests = handler_for()
        async with AsyncNmClient(extract, api_details=DETAILS, transport=httpx.MockTransport(handler)) as client:
            assert [r async for r in client.iter_lookup([])] == []
        assert not requests
    asyncio.run(run())


def test_context_precedence_missing_values_and_explicit_results():
    context = NaicsCodeContext(name="Acme", address="1 Main St")
    assert context.nm_result is None and context.nm_naics_code is None
    assert context.get_naics_code() is None and context.is_missing()
    assert context.naics2_code is None and context.naics4_code is None
    assert context.naics_desc == context.naics_subdesc == "Unknown"
    assert context.apply_r6_result("987654") is context
    assert context.naics_code == "987654" and not context.is_missing()
    assert context.naics2_code == "98" and context.naics4_code == "9876"
    submission = Submission(name="Acme", address="1 Main St")
    result = NmLookupResult(submission=submission, status="found", naics="123456")
    assert context.apply_nm_result(result) is context and context.nm_result is result
    assert context.get_naics_code() == "123456"
    assert context.naics_desc == "Example Neural Metrics NAICS Description"
    assert context.naics_subdesc == "Example Neural Metrics NAICS Sub-Description"
    context.agent_entered_code = "111111"
    assert context.naics_code == "111111"
    with pytest.raises(ValidationError):
        context.agent_entered_code = "bad"
    assert context.naics_code == "111111"
    context.agent_entered_code = None
    for status in ["not_found", "pending", "error"]:
        kwargs = {"error_code": "NM_TIMEOUT"} if status == "error" else {}
        context.apply_nm_result(NmLookupResult(submission=submission, status=status, **kwargs))
        assert context.nm_result.status == status and context.naics_code == "987654"
    context.apply_r6_result(None)
    assert context.is_missing() and context.naics_code is None
    with pytest.raises(ValueError, match="different business"):
        context.apply_nm_result(NmLookupResult(submission=Submission(name="Other"), **FOUND))
    with pytest.raises(ValueError, match="different business"):
        context.apply_nm_result(NmLookupResult(submission=Submission(name="Acme", address="Other"), **FOUND))


def test_r6_placeholder_never_fabricates_a_code():
    with pytest.raises(NotImplementedError, match="not been implemented"):
        get_relativity6_naics_code("Acme", "1 Main St")
