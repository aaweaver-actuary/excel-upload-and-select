"""Small Pydantic boundaries for NM requests and normalized lookup outcomes."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Annotated, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr, computed_field, field_validator, model_validator

NaicsCode = Annotated[str, Field(strict=True, min_length=6, max_length=6, pattern=r"^[0-9]{6}$")]


class NmModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, validate_default=True)


class NmApiDetails(NmModel):
    """Defaults read the current environment when an instance is constructed."""

    key: SecretStr = Field(default_factory=lambda: os.getenv("NEURALMETRICS_API_KEY", ""), repr=False)
    pem_path: Path | None = Field(default_factory=lambda: Path(value) if (value := os.getenv("PEM_PATH")) else None)

    # Configuration accepts strings for secrets and paths, unlike response models.
    model_config = ConfigDict(strict=False)

    @field_validator("key")
    @classmethod
    def valid_key(cls, key: SecretStr) -> SecretStr:
        value = key.get_secret_value()
        if not value.strip() or "\r" in value or "\n" in value:
            raise ValueError("A nonempty NEURALMETRICS_API_KEY is required.")
        return key


class Submission(NmModel):
    name: str = Field(min_length=1, serialization_alias="companyName")
    address: str = Field(default="", serialization_alias="companyAddress")
    country: str = Field(default="US", min_length=1)
    id: str | None = Field(default=None, min_length=1)
    lean_crawling: bool = Field(default=False, serialization_alias="leanCrawling")
    force_recrawl: bool = Field(default=False, serialization_alias="forceRecrawl")
    force_content_cache_refresh: bool = Field(default=False, serialization_alias="forceContentCacheRefresh")
    lro_submission: bool = Field(default=False, serialization_alias="lroSubmission")
    property_details: bool = Field(default=False, serialization_alias="propertyDetails")

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, name: str) -> str:
        if not name.strip():
            raise ValueError("name must not be blank.")
        return name

    @model_validator(mode="after")
    def identify(self) -> Self:
        if self.id is None:
            # Structured input avoids collisions such as ("AB", "C") / ("A", "BC").
            identity = json.dumps([self.name, self.address, self.country], ensure_ascii=False)
            object.__setattr__(self, "id", sha256(identity.encode("utf-8")).hexdigest())
        return self

    @property
    def key(self) -> str:
        return cast(str, self.id)

    @property
    def payload(self) -> dict:
        return NmBatchRequest(company_data=[self]).model_dump(mode="json", by_alias=True)


class NmBatchRequest(NmModel):
    company_data: list[Submission] = Field(min_length=1, serialization_alias="companyData")


class NmSessionResponse(BaseModel):
    """Observed session contract; additional vendor metadata is allowed."""

    model_config = ConfigDict(extra="ignore", strict=True)
    session_token: str = Field(alias="sessionToken", min_length=1, repr=False)

    @field_validator("session_token")
    @classmethod
    def valid_token(cls, token: str) -> str:
        if not token.strip() or "\r" in token or "\n" in token:
            raise ValueError("NM returned an invalid session token.")
        return token


class _Outcome(NmModel):
    status: Literal["found", "not_found", "pending", "error"]
    naics: NaicsCode | None = None

    @model_validator(mode="after")
    def consistent_code(self) -> Self:
        if (self.status == "found") != (self.naics is not None):
            raise ValueError("Only a found outcome may contain a NAICS code, and it must contain one.")
        return self


class NmClassification(_Outcome):
    """An extractor must explicitly classify the decoded NM response."""

    status: Literal["found", "not_found", "pending"]


class NmLookupResult(_Outcome):
    submission: Submission
    input_index: int | None = Field(default=None, ge=0)
    error_code: str | None = None

    @model_validator(mode="after")
    def consistent_error(self) -> Self:
        if (self.status == "error") != bool(self.error_code):
            raise ValueError("An error outcome must contain an error code; other outcomes must not.")
        return self

    @computed_field
    @property
    def returns_naics(self) -> bool:
        return self.status == "found" and self.naics is not None
