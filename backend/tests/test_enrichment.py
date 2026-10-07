import asyncio
from dataclasses import replace
import json

import pytest

from app.accounts import CanonicalAccount, normalize, validate_account
from app.columns import Settings
from app.enrichment import BusinessIdentity, NaicsReference, NaicsResolver, ProviderFailure, ProviderResult
from app.job_models import JobMetadata, ScoreResult
from app.scoring import FeatureBuilder, ReferenceDataService, score_accounts
from test_jobs import FakeScorer, setup


@pytest.mark.parametrize("value,field,expected", [
    (None, "naics", None), ("  ", "business_name", None), (" Name ", "business_name", "Name"),
    ("ny", "state", "NY"), (541330.0, "naics", "541330"), ("541330.0", "naics", "541330"),
    ("541330", "naics", "541330"), (123.0, "postal_code", "00123"), ("01234", "postal_code", "01234"),
    ("12345-6789", "postal_code", "12345-6789"), (1.25, "account_id", "1.25"),
])
def test_normalization(value, field, expected):
    assert normalize(value, field) == expected


@pytest.mark.parametrize("postal,issues", [("bad", ["INVALID_POSTAL_CODE"]), ("12345-6789", []), ("12345-67x9", ["INVALID_POSTAL_CODE"]), (None, [])])
def test_account_validation(postal, issues):
    assert validate_account(CanonicalAccount(source_row_number=2, business_name="Alpha", postal_code=postal)) == issues


def test_settings_are_centralized_and_checked(monkeypatch):
    monkeypatch.setenv("MAX_ROWS", "5000")
    monkeypatch.setenv("PIPELINE_VERSION", "git-sha")
    assert Settings.from_environment().max_rows == 5000
    assert Settings.from_environment().pipeline_version == "git-sha"
    monkeypatch.setenv("MAX_ROWS", "-1")
    with pytest.raises(ValueError, match="negative"):
        Settings.from_environment()
    monkeypatch.setenv("MAX_ROWS", "5000")
    monkeypatch.setenv("NAICS_MAX_CONCURRENCY", "0")
    with pytest.raises(ValueError, match="positive"):
        Settings.from_environment()


class Provider:
    name, version = "fake", "1"

    def __init__(self, outcomes):
        self.outcomes, self.calls, self.active, self.maximum = outcomes, 0, 0, 0

    async def lookup(self, identity):
        self.calls += 1
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        result = self.outcomes[min(self.calls - 1, len(self.outcomes) - 1)]
        if isinstance(result, Exception):
            raise result
        return result


def resolver_setup(setup, outcomes, **settings_overrides):
    settings, repo, store = setup
    metadata = JobMetadata(sheet_name="Accounts", mapping={"business_name": "A"})
    repo.create("job", "input.xlsx", "input", metadata, 1, {})
    provider = Provider(outcomes)
    return NaicsResolver(provider, NaicsReference({"541330"}, "test"), repo, replace(settings, **settings_overrides)), provider, repo


@pytest.mark.parametrize("outcome,expected,calls", [
    (ProviderResult(status="found", naics="541330"), "enriched", 1),
    (ProviderResult(status="not_found"), "not_found", 1),
    (ProviderResult(status="ambiguous"), "ambiguous", 1),
    (TimeoutError(), "provider_error", 3),
    (ConnectionError(), "provider_error", 3),
    (ProviderFailure("NAICS_PROVIDER_AUTH", False), "provider_error", 1),
    (ProviderFailure("NAICS_PROVIDER_RATE_LIMIT", True, 0), "provider_error", 3),
    (ProviderFailure("NAICS_PROVIDER_RATE_LIMIT", True, 100), "provider_error", 1),
    (ProviderFailure("NAICS_PROVIDER_RATE_LIMIT", True, float("nan")), "provider_error", 1),
    (ProviderFailure("NAICS_PROVIDER_RATE_LIMIT", True, -1), "provider_error", 1),
    (ProviderFailure("NAICS_PROVIDER_RATE_LIMIT", True, "bad"), "provider_error", 1),
    (ProviderResult(status="unexpected"), "provider_error", 1),
    (ProviderResult(status="found", naics="bogus"), "provider_error", 1),
    (ValueError("sensitive payload"), "provider_error", 1),
    ({"malformed": True}, "provider_error", 1),
])
def test_provider_results_and_bounded_failures(setup, outcome, expected, calls):
    resolver, provider, repo = resolver_setup(setup, [outcome])
    account = CanonicalAccount(source_row_number=2, business_name="Alpha")
    result = asyncio.run(resolver.resolve([account], {2: None}, "job"))[2]
    assert result.status == expected and provider.calls == calls
    assert len(repo.enrichments("job")) == 1
    if expected == "provider_error":
        assert resolver.metrics["provider_errors"] >= 1
        assert repo.cache_get(BusinessIdentity(business_name="Alpha").cache_key("fake", "1:test")) is None


def test_real_timeout_cancels_provider_and_bounds_concurrency(setup):
    resolver, provider, repo = resolver_setup(setup, [ProviderResult(status="found", naics="541330")],
                                            naics_max_concurrency=2, naics_request_timeout_seconds=0.005, naics_max_retries=0)
    accounts = [CanonicalAccount(source_row_number=number, business_name=str(number)) for number in range(2, 8)]
    asyncio.run(resolver.resolve(accounts, {number: None for number in range(2, 8)}, "job"))
    assert provider.maximum == 2 and provider.calls == 6

    async def slow(identity):
        await asyncio.sleep(1)

    provider.lookup = slow
    account = CanonicalAccount(source_row_number=8, business_name="Timeout")
    result = asyncio.run(resolver.resolve([account], {8: None}, "job"))[8]
    assert result.warning_codes == ["NAICS_PROVIDER_TIMEOUT"]


def test_retry_recovers_and_negative_cache_retains_timestamp(setup):
    resolver, provider, repo = resolver_setup(setup, [ProviderFailure("NAICS_PROVIDER_500", True), ProviderResult(status="not_found")])
    account = CanonicalAccount(source_row_number=2, business_name="Alpha")
    result = asyncio.run(resolver.resolve([account], {2: None}, "job"))[2]
    assert provider.calls == 2
    key = BusinessIdentity(business_name="Alpha").cache_key("fake", "1:test")
    cached = repo.cache_get(key)
    assert ProviderResult.model_validate(cached).retrieved_at == result.retrieved_at
    repo.cache_put(key, cached, -1)
    assert repo.cache_get(key) is None


def test_submitted_codes_reference_membership_and_unverified_provider(setup):
    resolver, provider, repo = resolver_setup(setup, [ProviderResult(status="found", naics="541330")])
    accounts = [CanonicalAccount(source_row_number=2, business_name="Alpha", naics="541330"),
                CanonicalAccount(source_row_number=3, business_name="Beta", naics="541330")]
    results = asyncio.run(resolver.resolve(accounts, {2: "541330", 3: 541330.0}, "job"))
    assert results[2].status == "accepted" and results[3].status == "normalized" and provider.calls == 0
    assert NaicsReference({"541330"}).check("999999") == "invalid"
    resolver.reference = NaicsReference()
    accounts = [CanonicalAccount(source_row_number=4, business_name="Unverified", naics="541330"),
                CanonicalAccount(source_row_number=5, business_name="Lookup")]
    results = asyncio.run(resolver.resolve(accounts, {4: "541330", 5: ""}, "job"))
    assert results[4].status == "unverified"
    assert results[5].warning_codes == ["NAICS_REFERENCE_NOT_CONFIGURED"]


def test_partial_scoring_is_independent_and_missing_outputs_are_errors():
    features = {2: {"naics": "541330"}, 3: {"naics": None}, 4: {"naics": "541330"}}

    class Other(FakeScorer):
        name, required_fields = "Score B", ()

    results = score_accounts(features, [FakeScorer(), Other()], {4})
    assert results[2]["Score A"].value == 0.73
    assert results[3]["Score A"].status == "missing_required_input"
    assert results[3]["Score B"].value == 0.73
    assert results[4]["Score B"].status == "invalid_input"

    class Broken(Other):
        def score(self, features):
            raise ValueError("sensitive payload")

    assert score_accounts(features, [Broken(), FakeScorer()], set())[2]["Score B"].status == "model_error"

    class Incomplete(Other):
        def score(self, features):
            return {}

    assert score_accounts(features, [Incomplete()], set())[2]["Score B"].status == "model_error"

    class BadResponse(Other):
        def score(self, features):
            return {2: {"bad": True}}

    assert score_accounts(features, [BadResponse()], set())[2]["Score B"].status == "model_error"


def test_malformed_score_does_not_hide_other_rows():
    class Mixed(FakeScorer):
        def score(self, features):
            return {2: ScoreResult(status="scored"), 3: ScoreResult(status="scored", value=1),
                    4: {"status": "scored", "value": float("nan")}}

    results = score_accounts({number: {"naics": "541330"} for number in range(2, 5)}, [Mixed()], set())
    assert results[2]["Score A"].status == "model_error"
    assert results[3]["Score A"].value == 1
    assert results[4]["Score A"].status == "model_error"


def test_progress_is_chunked_instead_of_written_per_lookup(setup):
    resolver, provider, repo = resolver_setup(setup, [ProviderResult(status="found", naics="541330")])
    accounts = [CanonicalAccount(source_row_number=number, business_name=str(number)) for number in range(2, 202)]
    updates = []
    asyncio.run(resolver.resolve(accounts, {account.source_row_number: None for account in accounts}, "job", updates.append))
    assert updates == [104, 200] and provider.calls == 200
