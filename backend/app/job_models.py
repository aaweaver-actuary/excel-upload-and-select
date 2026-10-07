from datetime import datetime
from typing import Literal

from pydantic import Field, FiniteFloat

from .models import Model

JobStatus = Literal["queued", "running", "completed", "completed_with_issues", "failed"]
RowStatus = Literal["scored", "scored_with_warnings", "needs_review", "invalid"]


class JobMetadata(Model):
    sheet_name: str = Field(min_length=1)
    mapping: dict[str, str | None]
    confirmedFields: list[str] = Field(default_factory=list)


class NaicsResolution(Model):
    input_value: str | int | float | bool | None = None
    final_value: str | None = None
    source: Literal["submitted", "third_party", "none"] = "none"
    status: str
    provider: str | None = None
    provider_record_id: str | None = None
    provider_confidence: float | None = None
    retrieved_at: datetime | None = None
    warning_codes: list[str] = Field(default_factory=list)


class ScoreResult(Model):
    value: FiniteFloat | None = None
    status: str
    issues: list[str] = Field(default_factory=list)


class RowResult(Model):
    source_row_number: int
    status: RowStatus
    issues: list[str]
    naics: NaicsResolution
    scores: dict[str, ScoreResult] = Field(default_factory=dict)


class ApplicationError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
