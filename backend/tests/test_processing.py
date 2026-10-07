from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.columns import FIELDS, SETTINGS, Field
from app.models import ProcessRequest
from app.processing import normalize_value, process_rows


def request(**overrides):
    data = {"columns": [{"id": "A", "label": "Email"}], "rows": [{"A": " example@test.com "}], "mapping": {"email": "A"}}
    return ProcessRequest(**(data | overrides))


@pytest.mark.parametrize("value,expected", [(" text ", "text"), (" \t ", None), (None, None), (False, False), (True, True), (0, 0), (1.25, 1.25)])
def test_normalization_preserves_scalar_types(value, expected):
    result = normalize_value(value)
    assert result == expected and type(result) is type(expected)


def test_every_row_is_processed_with_only_ten_in_preview():
    result = process_rows(request(rows=[{"A": f" row {index} "} for index in range(12)]), FIELDS, SETTINGS)
    assert result["rowsReceived"] == result["rowsProcessed"] == 12
    assert result["nonEmptyCounts"]["email"] == 12
    assert len(result["previewRows"]) == 10
    assert result["previewRows"][0] == {field.key: "row 0" if field.key == "email" else None for field in FIELDS}
    assert result["mappedFields"] == ["email"]
    assert len(result["unmappedFields"]) == 5


def test_missing_cells_and_whitespace_are_null():
    result = process_rows(request(rows=[{}, {"A": " "}, {"A": False}, {"A": 0}]), FIELDS, SETTINGS)
    assert [row["email"] for row in result["previewRows"]] == [None, None, False, 0]
    assert result["nonEmptyCounts"]["email"] == 2


@pytest.mark.parametrize("changes,message", [
    ({"columns": [{"id": "A", "label": "Email"}, {"id": "A", "label": "Phone"}]}, "IDs must be unique"),
    ({"mapping": {"unknown": "A"}}, "unknown destination"),
    ({"confirmedFields": ["unknown"]}, "unknown destination"),
    ({"mapping": {}}, "at least one"),
    ({"mapping": {"email": None}}, "at least one"),
    ({"mapping": {"email": "Z"}}, "unknown source"),
    ({"mapping": {"email": "A", "phone": "A"}}, "mapped once"),
    ({"rows": [{"Z": "x"}]}, "row references unknown"),
    ({"columns": [{"id": "A", "label": "Emial"}]}, "Confirm the mapping"),
    ({"columns": [{"id": "A", "label": "zzzzz"}]}, "Confirm the mapping"),
])
def test_invalid_imports_are_rejected(changes, message):
    with pytest.raises(ValueError, match=message):
        process_rows(request(**changes), FIELDS, SETTINGS)


def test_required_fields_and_row_limit_are_configurable():
    fields = (Field("email", "Email"), Field("phone", "Phone", required=True))
    with pytest.raises(ValueError, match="required field"):
        process_rows(request(), fields, SETTINGS)
    with pytest.raises(ValueError, match="limited to 1 rows"):
        process_rows(request(rows=[{}, {}]), FIELDS, replace(SETTINGS, max_rows=1))
    assert process_rows(request(), (Field("email", "Email", required=True),), replace(SETTINGS, max_rows=1))["rowsProcessed"] == 1


@pytest.mark.parametrize("label", ["Emial", "zzzzz"])
def test_confirmed_fuzzy_and_manual_mappings_are_processed(label):
    result = process_rows(request(columns=[{"id": "A", "label": label}], confirmedFields=["email"]), FIELDS, SETTINGS)
    assert result["rowsProcessed"] == 1


def test_duplicate_exact_columns_need_confirmation():
    data = request(columns=[{"id": "A", "label": "Email"}, {"id": "B", "label": "Email"}])
    with pytest.raises(ValueError, match="Confirm"):
        process_rows(data, FIELDS, SETTINGS)
    assert process_rows(data.model_copy(update={"confirmedFields": ["email"]}), FIELDS, SETTINGS)["rowsProcessed"] == 1


def test_ambiguous_optional_fields_must_be_explicitly_skipped():
    data = request(columns=[{"id": "A", "label": "Email"}, {"id": "B", "label": "Email"}, {"id": "C", "label": "First Name"}], mapping={"firstName": "C", "email": None})
    with pytest.raises(ValueError, match="Confirm"):
        process_rows(data, FIELDS, SETTINGS)
    assert process_rows(data.model_copy(update={"confirmedFields": ["email"]}), FIELDS, SETTINGS)["rowsProcessed"] == 1


@pytest.mark.parametrize("overrides", [{"rows": []}, {"columns": []}, {"rows": [{"A": {"nested": True}}]}, {"rows": [{"A": float("inf")}]}, {"unexpected": 1}])
def test_request_structure_rejects_invalid_values(overrides):
    with pytest.raises(ValidationError):
        request(**overrides)
