import type { DataRow, SourceColumn } from '../../types';
import { BaseTable } from '../base/BaseTable';
import { BaseTableHead } from '../base/BaseTableHead';
import { BaseTableBody } from '../base/BaseTableBody';
import { BaseTableRow } from '../base/BaseTableRow';
import { BaseTableHeader } from '../base/BaseTableHeader';
import { BaseTableCell } from '../base/BaseTableCell';
import { TableContainer } from '../shared/TableContainer';

export function WorkbookPreviewTable({ columns, rows }: { columns: SourceColumn[]; rows: DataRow[] }) {
  return <TableContainer><BaseTable>
    <BaseTableHead><BaseTableRow>{columns.map(column =>
      <BaseTableHeader key={column.id}>{column.label || `Unnamed column ${column.id}`}</BaseTableHeader>
    )}</BaseTableRow></BaseTableHead>
    <BaseTableBody>{rows.map((row, index) => <BaseTableRow key={index}>{columns.map(column =>
      <BaseTableCell key={column.id}>{String(row[column.id] ?? '')}</BaseTableCell>
    )}</BaseTableRow>)}</BaseTableBody>
  </BaseTable></TableContainer>;
}
