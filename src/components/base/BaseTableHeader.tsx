import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseTableHeader.module.css';

export type BaseTableHeaderProps = ComponentPropsWithoutRef<'th'>;

export function BaseTableHeader({ className, ...props }: BaseTableHeaderProps) {
  return <th {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
