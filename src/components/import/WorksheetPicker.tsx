import { BaseContainer } from '../base/BaseContainer';
import { BaseStrong } from '../base/BaseStrong';
import { BaseOption } from '../base/BaseOption';
import { LabeledSelect } from '../shared/LabeledSelect';
import styles from './WorksheetPicker.module.css';

export interface WorksheetPickerProps {
  filename: string;
  worksheets: Array<{ id: number; name: string }>;
  selectedId: number;
  onSelect: (id: number) => void;
}

export function WorksheetPicker({ filename, worksheets, selectedId, onSelect }: WorksheetPickerProps) {
  return <BaseContainer className={styles.metadata}>
    <BaseStrong>{filename}</BaseStrong>
    <LabeledSelect label="Worksheet " value={selectedId} className={styles.select} onChange={event => onSelect(Number(event.target.value))}>
      {worksheets.map(sheet => <BaseOption key={sheet.id} value={sheet.id}>{sheet.name}</BaseOption>)}
    </LabeledSelect>
  </BaseContainer>;
}
