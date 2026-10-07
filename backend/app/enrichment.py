"""Provider-independent NAICS resolution with bounded external work."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import random
import re
import time
from typing import Protocol

from pydantic import Field

from .accounts import CanonicalAccount, normalize
from .job_models import NaicsResolution
from .models import Model

logger = logging.getLogger(__name__)


class BusinessIdentity(Model):
    business_name: str
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None

    def cache_key(self, provider: str, version: str):
        values = {key: " ".join((value or "").casefold().split()) for key, value in self.model_dump().items()}
        return hashlib.sha256(json.dumps([provider, version, values], sort_keys=True).encode()).hexdigest()


class ProviderResult(Model):
    status: str
    naics: str | None = None
    record_id: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    retrieved_at: datetime | None = None


class ProviderFailure(Exception):
    def __init__(self, code="NAICS_PROVIDER_ERROR", retryable=False, retry_after=None):
        super().__init__(code)
        self.code, self.retryable, self.retry_after = code, retryable, retry_after


class NaicsProvider(Protocol):
    name: str
    version: str
    async def lookup(self, identity: BusinessIdentity) -> ProviderResult: ...


class UnconfiguredProvider:
    name = "none"
    version = "unconfigured"

    async def lookup(self, identity):
        return ProviderResult(status="not_configured")


class NaicsReference:
    """Inject a complete, approved code set and its version; never assume membership."""
    def __init__(self, codes: set[str] | None = None, version: str = "unconfigured"):
        self.codes, self.version = codes, version

    def check(self, value):
        if not value or not re.fullmatch(r"[0-9]{6}", value):
            return "invalid"
        if self.codes is None:
            return "unverified"
        return "valid" if value in self.codes else "invalid"


class NaicsResolver:
    def __init__(self, provider, reference, repository, settings):
        self.provider, self.reference, self.repository, self.settings = provider, reference, repository, settings
        self.semaphore = asyncio.Semaphore(settings.naics_max_concurrency)
        self.metrics = {"requested": 0, "cache_hits": 0, "provider_attempts": 0,
                        "provider_errors": 0, "rate_limited": 0, "provider_latency_seconds": 0.0}

    async def _lookup(self, identity, job_id):
        key = identity.cache_key(self.provider.name, self.provider.version + ":" + self.reference.version)
        cached = self.repository.cache_get(key)
        if cached is not None:
            self.metrics["cache_hits"] += 1
            return ProviderResult.model_validate(cached)
        self.metrics["requested"] += 1
        async with self.semaphore:
            attempt = 0
            while True:
                started = time.monotonic()
                category = "provider_error"
                self.metrics["provider_attempts"] += 1
                try:
                    result = await asyncio.wait_for(self.provider.lookup(identity), self.settings.naics_request_timeout_seconds)
                    result = ProviderResult.model_validate(result)
                    if result.status not in {"found", "not_found", "ambiguous", "not_configured"}:
                        raise ProviderFailure()
                    if result.status == "found" and self.reference.check(normalize(result.naics, "naics")) == "invalid":
                        raise ProviderFailure("NAICS_PROVIDER_INVALID_RESPONSE")
                    result.retrieved_at = result.retrieved_at or datetime.now(timezone.utc)
                    category = result.status
                    if result.status in {"found", "not_found", "ambiguous"}:
                        self.repository.cache_put(key, result.model_dump(mode="json"), self.settings.naics_cache_ttl)
                    return result
                except (TimeoutError, ConnectionError) as error:
                    failure = ProviderFailure("NAICS_PROVIDER_TIMEOUT" if isinstance(error, TimeoutError) else "NAICS_PROVIDER_ERROR", True)
                except ProviderFailure as error:
                    failure = error
                except Exception:
                    failure = ProviderFailure("NAICS_PROVIDER_INVALID_RESPONSE")
                finally:
                    elapsed = time.monotonic() - started
                    self.metrics["provider_latency_seconds"] += elapsed
                    logger.info("provider_attempt", extra={"job_id": job_id, "stage": "enrichment",
                                "provider": self.provider.name, "attempt": attempt + 1, "latency": elapsed, "result_category": category})
                self.metrics["provider_errors"] += 1
                if failure.code == "NAICS_PROVIDER_RATE_LIMIT":
                    self.metrics["rate_limited"] += 1
                if not failure.retryable or attempt == self.settings.naics_max_retries:
                    return ProviderResult(status=failure.code)
                delay = failure.retry_after if failure.retry_after is not None else (
                    self.settings.naics_retry_base_seconds * 2 ** attempt * random.uniform(0.5, 1.5))
                # A provider-requested wait beyond our request budget is not retried early.
                if not isinstance(delay, (int, float)) or not math.isfinite(delay) or delay < 0 or delay > self.settings.naics_request_timeout_seconds:
                    return ProviderResult(status=failure.code)
                await asyncio.sleep(max(0, delay))
                attempt += 1

    async def resolve(self, accounts: list[CanonicalAccount], submitted: dict, job_id: str, progress=None):
        saved = self.repository.enrichments(job_id)
        resolutions, groups = {}, {}
        for account in accounts:
            number = account.source_row_number
            raw = submitted[number]
            check = self.reference.check(account.naics)
            warning = ["INVALID_SUBMITTED_NAICS"] if normalize(raw, "naics") is not None and check == "invalid" else []
            if not account.business_name:
                resolutions[number] = NaicsResolution(input_value=raw, status="insufficient_identity", warning_codes=warning)
            elif number in saved and saved[number]["status"] not in {"provider_error", "not_configured"}:
                resolutions[number] = NaicsResolution.model_validate(saved[number])
            elif check in {"valid", "unverified"}:
                status = "unverified" if check == "unverified" else ("accepted" if raw == account.naics else "normalized")
                resolutions[number] = NaicsResolution(input_value=raw, final_value=account.naics, source="submitted", status=status,
                    warning_codes=["NAICS_REFERENCE_NOT_CONFIGURED"] if check == "unverified" else [])
            else:
                identity = BusinessIdentity(**{key: getattr(account, key) for key in BusinessIdentity.model_fields})
                key = identity.cache_key(self.provider.name, self.provider.version)
                groups.setdefault(key, (identity, []))[1].append((number, raw, warning))

        async def resolve_group(identity, rows):
            provider_result = await self._lookup(identity, job_id)
            group_results = {}
            for number, raw, warnings in rows:
                found = provider_result.status == "found"
                final = normalize(provider_result.naics, "naics") if found else None
                if found and self.reference.check(final) == "unverified":
                    warnings = warnings + ["NAICS_REFERENCE_NOT_CONFIGURED"]
                if not found:
                    codes = {"not_found": "NAICS_NOT_FOUND", "ambiguous": "NAICS_AMBIGUOUS", "not_configured": "NAICS_PROVIDER_NOT_CONFIGURED"}
                    warnings = warnings + [codes.get(provider_result.status, provider_result.status)]
                resolution = NaicsResolution(input_value=raw, final_value=final, source="third_party" if found else "none",
                    status="enriched" if found else (provider_result.status if provider_result.status in {"not_found", "ambiguous", "not_configured"} else "provider_error"),
                    provider=self.provider.name, provider_record_id=provider_result.record_id,
                    provider_confidence=provider_result.confidence, retrieved_at=provider_result.retrieved_at,
                    warning_codes=warnings)
                group_results[number] = resolution
                resolutions[number] = resolution
            self.repository.save_enrichments(job_id, group_results)

        # Fixed-size task windows avoid allocating thousands of waiting network tasks.
        pending = list(groups.values())
        last_progress = 0
        for offset in range(0, len(pending), self.settings.naics_max_concurrency):
            await asyncio.gather(*(resolve_group(identity, rows) for identity, rows in pending[offset:offset + self.settings.naics_max_concurrency]))
            if progress and (len(resolutions) - last_progress >= 100 or offset + self.settings.naics_max_concurrency >= len(pending)):
                progress(len(resolutions))
                last_progress = len(resolutions)
        self.repository.save_enrichments(job_id, resolutions)
        return resolutions
