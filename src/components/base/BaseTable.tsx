import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseTable.module.css';

export type BaseTableProps = ComponentPropsWithoutRef<'table'>;

export function BaseTable({ className, ...props }: BaseTableProps) {
  return <table {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
