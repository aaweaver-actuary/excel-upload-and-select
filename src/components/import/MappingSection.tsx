import type { Mapping, Schema, SourceColumn, Suggestion } from '../../types';
import { BaseContainer } from '../base/BaseContainer';
import { BaseSubheader } from '../base/BaseSubheader';
import { BaseListItem } from '../base/BaseListItem';
import { HintParagraph } from '../shared/HintParagraph';
import { HintList } from '../shared/HintList';
import { MappingField } from './MappingField';
import { ProcessButton } from './ProcessButton';
import styles from './MappingSection.module.css';

export interface MappingSectionProps {
  fields: Schema['fields'];
  suggestions: Suggestion[];
  columns: SourceColumn[];
  mapping: Mapping;
  confirmed: string[];
  issues: string[];
  busy: boolean;
  onSelect: (fieldKey: string, columnId: string) => void;
  onApprove: (fieldKey: string) => void;
  onProcess: () => void;
}

export function MappingSection({ fields, suggestions, columns, mapping, confirmed, issues, busy, onSelect, onApprove, onProcess }: MappingSectionProps) {
  return <>
    <BaseSubheader>Column mapping</BaseSubheader>
    <HintParagraph>Exact matches are accepted automatically. Approve fuzzy suggestions, choose another column, or skip an optional field.</HintParagraph>
    <BaseContainer className={styles.grid}>{fields.map(field => <MappingField
      key={field.key}
      field={field}
      suggestion={suggestions.find(item => item.fieldKey === field.key)!}
      columns={columns}
      selected={mapping[field.key]}
      confirmed={confirmed}
      busy={busy}
      onSelect={onSelect}
      onApprove={onApprove}
    />)}</BaseContainer>
    {issues.length > 0 && <HintList>{issues.map(issue => <BaseListItem key={issue}>{issue}</BaseListItem>)}</HintList>}
    <ProcessButton disabled={busy || issues.length > 0} onClick={onProcess} />
  </>;
}
