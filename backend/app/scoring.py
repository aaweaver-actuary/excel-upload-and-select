"""Explicit extension points: all business features and scores belong here."""
from typing import Protocol
import re

from .job_models import ScoreResult


class ReferenceDataService:
    version = "unconfigured"

    def lookup(self, account, naics):
        return {}


class FeatureBuilder:
    def build(self, accounts, resolutions, reference):
        return {account.source_row_number: account.model_dump() | {"naics": resolutions[account.source_row_number].final_value}
                | reference.lookup(account, resolutions[account.source_row_number]) for account in accounts}


class Scorer(Protocol):
    name: str
    version: str
    required_fields: tuple[str, ...]
    def score(self, features: dict[int, dict]) -> dict[int, ScoreResult]: ...


def score_accounts(features, scorers, invalid_rows):
    results = {number: {} for number in features}
    for scorer in scorers:
        eligible = {}
        for number, row in features.items():
            if number in invalid_rows:
                results[number][scorer.name] = ScoreResult(status="invalid_input")
            elif any(row.get(field) is None for field in scorer.required_fields):
                code = re.sub(r"[^A-Z0-9]+", "_", scorer.name.upper()).strip("_")
                results[number][scorer.name] = ScoreResult(status="missing_required_input", issues=[f"MISSING_{code}_INPUT"])
            else:
                eligible[number] = row
        try:
            scored = scorer.score(eligible) if eligible else {}
        except Exception:
            scored = {}
        for number in eligible:
            try:
                result = ScoreResult.model_validate(scored.get(number))
                if result.status == "scored" and result.value is None:
                    raise ValueError("Scored result requires a finite value.")
            except Exception:
                result = ScoreResult(status="model_error", issues=["MODEL_ERROR"])
            results[number][scorer.name] = result
    return results
