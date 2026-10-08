"""NAICS source selection without network work hidden in property access."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from ..get_naics_description import get_naics_description
from ..get_naics_subdescription import get_naics_subdescription
from .models import NaicsCode, NmLookupResult


class NaicsCodeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, strict=True)

    name: str = Field(min_length=1)
    address: str = ""
    agent_entered_code: NaicsCode | None = None
    r6_naics_code: NaicsCode | None = None
    _nm_result: NmLookupResult | None = PrivateAttr(default=None)

    def apply_nm_result(self, result: NmLookupResult) -> Self:
        """Record every outcome, including misses; never call NM implicitly."""
        if result.submission.name != self.name or result.submission.address != self.address:
            raise ValueError("NM result belongs to a different business.")
        self._nm_result = result
        return self

    def apply_r6_result(self, code: str | None) -> Self:
        """Record a future caller-supplied R6 code without invoking its API."""
        self.r6_naics_code = code
        return self

    @property
    def nm_result(self) -> NmLookupResult | None:
        return self._nm_result

    @property
    def nm_naics_code(self) -> str | None:
        return self._nm_result.naics if self._nm_result is not None else None

    @property
    def naics_code(self) -> str | None:
        return self.agent_entered_code or self.nm_naics_code or self.r6_naics_code

    def get_naics_code(self) -> str | None:
        return self.naics_code

    def is_missing(self) -> bool:
        return self.naics_code is None

    @property
    def naics2_code(self) -> str | None:
        code = self.naics_code
        return code[:2] if code is not None else None

    @property
    def naics4_code(self) -> str | None:
        code = self.naics_code
        return code[:4] if code is not None else None

    @property
    def naics_desc(self) -> str:
        code = self.naics_code
        return get_naics_description(int(code)) if code is not None else "Unknown"

    @property
    def naics_subdesc(self) -> str:
        code = self.naics_code
        return get_naics_subdescription(int(code)) if code is not None else "Unknown"
