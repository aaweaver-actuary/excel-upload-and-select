import type { RowResult } from '../../types';
import { BaseTable } from '../base/BaseTable';
import { BaseTableCaption } from '../base/BaseTableCaption';
import { BaseTableHead } from '../base/BaseTableHead';
import { BaseTableBody } from '../base/BaseTableBody';
import { BaseTableRow } from '../base/BaseTableRow';
import { BaseTableHeader } from '../base/BaseTableHeader';
import { TableContainer } from '../shared/TableContainer';
import { ResultTableRow } from './ResultTableRow';

export function ResultsTable({ rows, scorerNames }: { rows: RowResult[]; scorerNames: string[] }) {
  return <TableContainer><BaseTable>
    <BaseTableCaption>Backend processing outcomes</BaseTableCaption>
    <BaseTableHead><BaseTableRow>
      <BaseTableHeader scope="col">Source row</BaseTableHeader>
      <BaseTableHeader scope="col">Business name</BaseTableHeader>
      <BaseTableHeader scope="col">Status</BaseTableHeader>
      <BaseTableHeader scope="col">NAICS submitted</BaseTableHeader>
      <BaseTableHeader scope="col">NAICS final</BaseTableHeader>
      {scorerNames.map(name => <BaseTableHeader scope="col" key={name}>{name} · value / status</BaseTableHeader>)}
      <BaseTableHeader scope="col">Details</BaseTableHeader>
    </BaseTableRow></BaseTableHead>
    <BaseTableBody>{rows.map(row => <ResultTableRow key={row.source_row_number} row={row} scorerNames={scorerNames} />)}</BaseTableBody>
  </BaseTable></TableContainer>;
}
