"""Edit this file to change the import schema and matching/import defaults."""

from dataclasses import dataclass
import os
import math


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    aliases: tuple[str, ...] = ()
    required: bool = False


FIELDS = (
    Field("firstName", "First Name", ("firstname", "given name", "fname", "first")),
    Field("lastName", "Last Name", ("lastname", "surname", "lname", "family name", "familyname")),
    Field("email", "Email", ("e-mail", "email address", "e-mail address")),
    Field("phone", "Phone", ("telephone", "mobile", "cell", "phone number", "cell phone")),
    Field("company", "Company", ("organization", "org", "employer", "business")),
    Field("state", "State", ("province", "region", "location state", "state/province")),
)


@dataclass(frozen=True)
class Settings:
    suggestion_threshold: float = 80
    candidate_limit: int = 3
    max_rows: int = 50_000
    max_file_bytes: int = 20 * 1024 * 1024
    max_request_bytes: int = 64 * 1024 * 1024
    preview_rows: int = 10
    job_artifact_directory: str = ".cache/jobs"
    max_expanded_bytes: int = 200 * 1024 * 1024
    max_workbook_cells: int = 1_000_000
    worker_poll_interval: float = 1
    worker_max_attempts: int = 3
    worker_stale_seconds: float = 30
    naics_max_concurrency: int = 8
    naics_request_timeout_seconds: float = 10
    naics_max_retries: int = 2
    naics_retry_base_seconds: float = 0.5
    naics_cache_ttl: float = 86400
    artifact_retention_days: float = 0
    pipeline_version: str = "foundation-1"

    @classmethod
    def from_environment(cls):
        from dataclasses import fields
        defaults = cls()
        values = {}
        for field in fields(cls):
            default = getattr(defaults, field.name)
            value = os.getenv(field.name.upper())
            if value is not None:
                values[field.name] = type(default)(value)
        result = cls(**values)
        for field in fields(cls):
            value = getattr(result, field.name)
            if isinstance(value, (int, float)) and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{field.name.upper()} must be finite and not negative.")
        if not all((result.naics_max_concurrency, result.naics_request_timeout_seconds,
                    result.worker_poll_interval, result.worker_max_attempts, result.worker_stale_seconds)):
            raise ValueError("Concurrency, timeouts, polling and worker attempts must be positive.")
        return result


SETTINGS = Settings.from_environment()
