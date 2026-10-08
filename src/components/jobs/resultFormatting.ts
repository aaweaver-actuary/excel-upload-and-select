import type { CellValue, RowStatus } from '../../types';

export const rowStatusLabels: Record<RowStatus, string> = {
  scored: 'Scored',
  scored_with_warnings: 'Scored with warnings',
  needs_review: 'Needs review',
  invalid: 'Invalid',
};

export function readable(value: string) {
  return value.replace(/_/g, ' ').toLowerCase();
}

export function display(value: CellValue | undefined) {
  return value == null ? '—' : String(value);
}
