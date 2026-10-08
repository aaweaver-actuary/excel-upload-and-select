import type { ChangeEvent } from "react";
import { BaseInput } from "../base/BaseInput";
import { BaseLabel } from "../base/BaseLabel";
import { BaseSpan } from "../base/BaseSpan";
import styles from "./FilePicker.module.css";

export function FilePicker({ onSelect }: { onSelect: (file: File) => void }) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    onSelect(file);
    event.currentTarget.value = "";
  }

  return (
    <BaseLabel className={styles.label}>
      <BaseSpan>Choose Excel file</BaseSpan>
      <BaseInput
        className={styles.input}
        type="file"
        accept=".xlsx"
        onChange={handleChange}
      />
    </BaseLabel>
  );
}
