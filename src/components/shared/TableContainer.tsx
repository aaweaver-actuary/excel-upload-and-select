import { BaseContainer } from '../base/BaseContainer';
import type { BaseContainerProps } from '../base/BaseContainer';
import styles from './TableContainer.module.css';

export function TableContainer({ className, ...props }: BaseContainerProps) {
  return <BaseContainer {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
