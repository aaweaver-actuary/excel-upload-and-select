import type { ParsedSheet } from '../../types';
import { BaseSubheader } from '../base/BaseSubheader';
import { BaseParagraph } from '../base/BaseParagraph';
import { Section } from '../layout/Section';
import { WorkbookPreviewTable } from './WorkbookPreviewTable';

export function ColumnPreview({ parsed, previewRows }: { parsed: ParsedSheet; previewRows: number }) {
  return <Section>
    <BaseSubheader>Column preview</BaseSubheader>
    <BaseParagraph>{parsed.rows.length.toLocaleString()} rows imported. Showing the first {previewRows}.</BaseParagraph>
    <WorkbookPreviewTable columns={parsed.columns} rows={parsed.rows.slice(0, previewRows)} />
  </Section>;
}
