import { needsApproval } from "../../mapping";
import type { FieldDefinition, SourceColumn, Suggestion } from "../../types";
import { BaseButton } from "../base/BaseButton";
import { BaseContainer } from "../base/BaseContainer";
import { BaseSpan } from "../base/BaseSpan";
import { BaseOption } from "../base/BaseOption";
import { HintSpan } from "../shared/HintSpan";
import { LabeledSelect } from "../shared/LabeledSelect";
import styles from "./MappingField.module.css";

export interface MappingFieldProps {
  field: FieldDefinition;
  suggestion: Suggestion;
  columns: SourceColumn[];
  selected: string | null;
  confirmed: string[];
  busy: boolean;
  onSelect: (fieldKey: string, columnId: string) => void;
  onApprove: (fieldKey: string) => void;
}

export function MappingField({
  field,
  suggestion,
  columns,
  selected,
  confirmed,
  busy,
  onSelect,
  onApprove,
}: MappingFieldProps) {
  const pending = needsApproval(suggestion, selected, confirmed);
  return (
    <BaseContainer className={styles.field}>
      <LabeledSelect
        label={
          <BaseSpan>
            {field.label}
            {field.required ? " (required)" : ""}
          </BaseSpan>
        }
        labelClassName={styles.label}
        className={styles.select}
        value={selected ?? ""}
        onChange={(event) => onSelect(field.key, event.target.value)}
        disabled={busy}
      >
        <BaseOption value="">Not mapped / skip</BaseOption>
        {columns.map((column) => (
          <BaseOption key={column.id} value={column.id}>
            {column.label || "Unnamed"} ({column.id})
          </BaseOption>
        ))}
      </LabeledSelect>
      <HintSpan>
        {suggestion.matchType}
        {suggestion.score !== null &&
          ` · ${suggestion.score.toFixed(1)}% similarity`}
      </HintSpan>
      {suggestion.matchType === "ambiguous" && (
        <HintSpan>Choose a column explicitly or skip this field.</HintSpan>
      )}
      {pending &&
        (selected === null ? (
          <BaseButton disabled={busy} onClick={() => onSelect(field.key, "")}>
            Skip {field.label} mapping
          </BaseButton>
        ) : (
          <BaseButton disabled={busy} onClick={() => onApprove(field.key)}>
            Approve {field.label} mapping
          </BaseButton>
        ))}
    </BaseContainer>
  );
}
