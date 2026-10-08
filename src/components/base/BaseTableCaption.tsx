import type { ComponentPropsWithoutRef } from 'react';
import styles from './BaseTableCaption.module.css';

export type BaseTableCaptionProps = ComponentPropsWithoutRef<'caption'>;

export function BaseTableCaption({ className, ...props }: BaseTableCaptionProps) {
  return <caption {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
