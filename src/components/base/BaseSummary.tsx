import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseSummary.module.css';

export type BaseSummaryProps = ComponentPropsWithoutRef<'summary'>;

export function BaseSummary({ className, ...props }: BaseSummaryProps) {
  return <summary {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
