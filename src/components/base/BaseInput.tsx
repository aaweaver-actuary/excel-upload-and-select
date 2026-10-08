import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseInput.module.css';

export type BaseInputProps = ComponentPropsWithoutRef<'input'>;

export function BaseInput({ className, ...props }: BaseInputProps) {
  return <input {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
