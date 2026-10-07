import re
import unicodedata

from rapidfuzz import fuzz

from .columns import Field, Settings
from .models import Candidate, Column, Suggestion


def normalize_header(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("_", " ")
    return re.sub(r"[^\w]+", " ", value).strip()


def _suggestion(field: Field, candidates: list[tuple[Candidate, bool]], limit: int) -> Suggestion:
    if not candidates:
        return Suggestion(fieldKey=field.key, matchType="unmatched", columnId=None, score=None, candidates=[])
    best, exact = candidates[0]
    tied = len(candidates) > 1 and candidates[1][0].score == best.score and candidates[1][1] == exact
    return Suggestion(
        fieldKey=field.key,
        matchType="ambiguous" if tied else "exact" if exact else "fuzzy",
        columnId=None if tied else best.columnId,
        score=best.score,
        candidates=[candidate for candidate, _ in candidates[:limit]],
    )


def match_columns(columns: list[Column], fields: tuple[Field, ...], settings: Settings) -> list[Suggestion]:
    ranked: list[list[tuple[Candidate, bool]]] = []
    for field in fields:
        aliases = [normalize_header(value) for value in (field.key, field.label, *field.aliases)]
        candidates = []
        for column in columns:
            name = normalize_header(column.label)
            if not name:
                continue
            exact = name in aliases
            score = 100.0 if exact else max(fuzz.WRatio(name, alias) for alias in aliases)
            if exact or score >= settings.suggestion_threshold:
                candidates.append((Candidate(columnId=column.id, score=score), exact))
        candidates.sort(key=lambda candidate: (not candidate[1], -candidate[0].score))
        ranked.append(candidates)

    initial = [_suggestion(field, candidates, settings.candidate_limit) for field, candidates in zip(fields, ranked)]
    exact_columns = {suggestion.columnId for suggestion in initial if suggestion.matchType == "exact"}
    suggestions = []
    for field, candidates, initial_suggestion in zip(fields, ranked, initial):
        if initial_suggestion.matchType != "exact":
            candidates = [(candidate, exact) for candidate, exact in candidates if exact or candidate.columnId not in exact_columns]
        suggestions.append(_suggestion(field, candidates, settings.candidate_limit))

    used: dict[str, list[Suggestion]] = {}
    for suggestion in suggestions:
        if suggestion.columnId is not None:
            used.setdefault(suggestion.columnId, []).append(suggestion)
    for group in used.values():
        if len(group) > 1:
            for suggestion in group:
                suggestion.columnId = None
                suggestion.matchType = "ambiguous"
    return suggestions
