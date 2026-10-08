import type { RowStatus } from "../../types";
import { BaseOption } from "../base/BaseOption";
import { LabeledSelect } from "../shared/LabeledSelect";
import { rowStatusLabels } from "./resultFormatting";
import styles from "./ResultsFilter.module.css";

export function ResultsFilter({
  status,
  onSelect,
}: {
  status: RowStatus | "";
  onSelect: (status: RowStatus | "") => void;
}) {
  return (
    <LabeledSelect
      label="Row status "
      labelClassName={styles.label}
      className={styles.select}
      value={status}
      onChange={(event) => onSelect(event.target.value as RowStatus | "")}
    >
      <BaseOption value="">All rows</BaseOption>
      {Object.entries(rowStatusLabels).map(([value, label]) => (
        <BaseOption key={value} value={value}>
          {label}
        </BaseOption>
      ))}
    </LabeledSelect>
  );
}
