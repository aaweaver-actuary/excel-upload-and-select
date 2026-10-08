import { BaseSection } from '../base/BaseSection';
import type { BaseSectionProps } from '../base/BaseSection';
import styles from './Section.module.css';

export function Section({ className, ...props }: BaseSectionProps) {
  return <BaseSection {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
