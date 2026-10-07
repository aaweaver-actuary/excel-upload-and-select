from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictBool, StrictInt, StrictStr

CellValue = StrictStr | StrictBool | StrictInt | Annotated[FiniteFloat, Field(strict=True)] | None


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Column(Model):
    id: str = Field(min_length=1)
    label: str


class MatchRequest(Model):
    columns: list[Column] = Field(min_length=1)


class Candidate(Model):
    columnId: str
    score: float


class Suggestion(Model):
    fieldKey: str
    matchType: Literal["exact", "fuzzy", "ambiguous", "unmatched"]
    columnId: str | None
    score: float | None
    candidates: list[Candidate]


class ProcessRequest(MatchRequest):
    rows: list[dict[str, CellValue]] = Field(min_length=1)
    mapping: dict[str, str | None]
    confirmedFields: list[str] = Field(default_factory=list)
