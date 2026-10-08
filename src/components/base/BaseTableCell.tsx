import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseTableCell.module.css';

export type BaseTableCellProps = ComponentPropsWithoutRef<'td'>;

export function BaseTableCell({ className, ...props }: BaseTableCellProps) {
  return <td {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
