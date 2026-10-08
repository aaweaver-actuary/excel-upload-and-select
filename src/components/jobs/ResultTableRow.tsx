import type { RowResult } from '../../types';
import { BaseTableRow } from '../base/BaseTableRow';
import { BaseTableHeader } from '../base/BaseTableHeader';
import { BaseTableCell } from '../base/BaseTableCell';
import { RowDetails } from './RowDetails';
import { display, readable, rowStatusLabels } from './resultFormatting';

export function ResultTableRow({ row, scorerNames }: { row: RowResult; scorerNames: string[] }) {
  return <BaseTableRow>
    <BaseTableHeader scope="row">{row.source_row_number}</BaseTableHeader>
    <BaseTableCell>{display(row.canonical_account?.business_name)}</BaseTableCell>
    <BaseTableCell>{rowStatusLabels[row.status]}</BaseTableCell>
    <BaseTableCell>{display(row.naics.input_value)}</BaseTableCell>
    <BaseTableCell>{display(row.naics.final_value)}</BaseTableCell>
    {scorerNames.map(name => <BaseTableCell key={name}>
      {display(row.scores[name]?.value)} · {readable(row.scores[name]?.status ?? 'not_scored')}
    </BaseTableCell>)}
    <BaseTableCell><RowDetails row={row} /></BaseTableCell>
  </BaseTableRow>;
}
