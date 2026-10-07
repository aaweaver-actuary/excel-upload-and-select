from dataclasses import replace

import pytest
from rapidfuzz import fuzz

from app.columns import FIELDS, SETTINGS, Field
from app.matching import match_columns, normalize_header
from app.models import Column


def columns(*labels):
    return [Column(id=str(index), label=label) for index, label in enumerate(labels)]


@pytest.mark.parametrize("source,expected", [
    ("  Last__Name  ", "last name"), ("E-Mail Address", "e mail address"),
    ("Ｆｉｒｓｔ NAME", "first name"), ("ÉMAIL!", "émail"), ("!!!", ""),
])
def test_normalization(source, expected):
    assert normalize_header(source) == expected


def test_existing_aliases_are_unique_exact_matches():
    result = match_columns(columns("First Name", "Surname", "E-mail address", "Cell Phone", "Employer", "State/Province"), FIELDS, SETTINGS)
    assert [item.columnId for item in result] == ["0", "1", "2", "3", "4", "5"]
    assert all(item.matchType == "exact" and item.score == 100 for item in result)


def test_unknown_and_blank_headers_are_unmatched():
    result = match_columns(columns("", "!!!", "zzzzzzzz"), FIELDS, SETTINGS)
    assert all(item.matchType == "unmatched" and item.columnId is None and item.score is None for item in result)


def test_typo_requires_review_and_threshold_boundary_is_inclusive():
    fields = (Field("email", "Email"),)
    score = fuzz.WRatio("emial", "email")
    settings = replace(SETTINGS, suggestion_threshold=score)
    result = match_columns(columns("Emial"), fields, settings)[0]
    assert result.matchType == "fuzzy"
    assert result.columnId == "0"
    assert result.score == score
    assert match_columns(columns("Emial"), fields, replace(settings, suggestion_threshold=score + 0.01))[0].matchType == "unmatched"


def test_equal_fuzzy_scores_and_duplicate_exact_headers_are_ambiguous():
    for labels in [("email", "E-Mail"), ("emial", "emial")]:
        result = match_columns(columns(*labels), (FIELDS[2],), SETTINGS)[0]
        assert result.matchType == "ambiguous"
        assert result.columnId is None
        assert [candidate.columnId for candidate in result.candidates] == ["0", "1"]


def test_unique_exact_match_beats_a_high_fuzzy_score():
    result = match_columns(columns("name first", "first name"), (Field("firstName", "First Name"),), SETTINGS)[0]
    assert result.matchType == "exact" and result.columnId == "1"
    assert result.candidates[1].score == 95


def test_reordered_tokens_still_require_approval():
    result = match_columns(columns("name first"), (Field("firstName", "First Name"),), SETTINGS)[0]
    assert result.matchType == "fuzzy" and result.score == 95


def test_exact_matches_reserve_columns_before_fuzzy_matching():
    fields = (Field("one", "Name"), Field("two", "Names"))
    result = match_columns(columns("Name"), fields, SETTINGS)
    assert result[0].matchType == "exact"
    assert result[1].matchType == "unmatched"


@pytest.mark.parametrize("labels", [("Name",), ("Nmae",)])
def test_competing_fields_require_manual_resolution(labels):
    result = match_columns(columns(*labels), (Field("one", "Name"), Field("two", "Name")), replace(SETTINGS, suggestion_threshold=70))
    assert all(item.matchType == "ambiguous" and item.columnId is None for item in result)


def test_candidate_count_is_limited_and_order_is_stable():
    result = match_columns(columns("emial", "emial", "emial", "emial"), (FIELDS[2],), SETTINGS)[0]
    assert [candidate.columnId for candidate in result.candidates] == ["0", "1", "2"]
