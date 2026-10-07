"""Replace process_rows with business-specific processing when ready."""

from .columns import Field, Settings
from .matching import match_columns
from .models import CellValue, ProcessRequest


def validate_columns(ids: list[str]) -> None:
    if len(ids) != len(set(ids)):
        raise ValueError("Source column IDs must be unique.")


def validate_import(request: ProcessRequest, fields: tuple[Field, ...], settings: Settings) -> None:
    column_ids = {column.id for column in request.columns}
    validate_columns([column.id for column in request.columns])
    field_keys = {field.key for field in fields}
    if (set(request.mapping) | set(request.confirmedFields)) - field_keys:
        raise ValueError("The mapping contains unknown destination fields.")
    selected = [column_id for column_id in request.mapping.values() if column_id is not None]
    if not selected:
        raise ValueError("Map at least one field before processing.")
    if set(selected) - column_ids:
        raise ValueError("The mapping references unknown source columns.")
    if len(selected) != len(set(selected)):
        raise ValueError("A source column can only be mapped once.")
    if any(field.required and request.mapping.get(field.key) is None for field in fields):
        raise ValueError("Map every required field before processing.")
    if len(request.rows) > settings.max_rows:
        raise ValueError(f"Imports are limited to {settings.max_rows:,} rows.")
    if any(set(row) - column_ids for row in request.rows):
        raise ValueError("A data row references unknown source columns.")
    for suggestion in match_columns(request.columns, fields, settings):
        selected_id = request.mapping.get(suggestion.fieldKey)
        needs_confirmation = suggestion.matchType == "ambiguous" or (selected_id is not None and not (
            suggestion.matchType == "exact" and suggestion.columnId == selected_id
        ))
        if needs_confirmation and suggestion.fieldKey not in request.confirmedFields:
            raise ValueError(f"Confirm the mapping for {suggestion.fieldKey} before processing.")


def normalize_value(value: CellValue) -> CellValue:
    if isinstance(value, str):
        return value.strip() or None
    return value


def process_rows(request: ProcessRequest, fields: tuple[Field, ...], settings: Settings) -> dict:
    validate_import(request, fields, settings)
    counts = {field.key: 0 for field in fields}
    preview = []
    for source_row in request.rows:
        row = {
            field.key: normalize_value(source_row.get(request.mapping.get(field.key)))
            for field in fields
        }
        for key, value in row.items():
            if value is not None:
                counts[key] += 1
        if len(preview) < settings.preview_rows:
            preview.append(row)
    return {
        "rowsReceived": len(request.rows),
        "rowsProcessed": len(request.rows),
        "mappedFields": [field.key for field in fields if request.mapping.get(field.key) is not None],
        "unmappedFields": [field.key for field in fields if request.mapping.get(field.key) is None],
        "nonEmptyCounts": counts,
        "previewRows": preview,
    }
