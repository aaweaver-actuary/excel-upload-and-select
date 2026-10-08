import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseSelect.module.css';

export type BaseSelectProps = ComponentPropsWithoutRef<'select'>;

export function BaseSelect({ className, ...props }: BaseSelectProps) {
  return <select {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
