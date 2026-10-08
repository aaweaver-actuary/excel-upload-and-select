import { BaseContainer } from '../base/BaseContainer';
import type { BaseContainerProps } from '../base/BaseContainer';
import styles from './AppShell.module.css';

export function AppShell({ className, ...props }: BaseContainerProps) {
  return <BaseContainer {...props} className={[styles.element, className].filter(Boolean).join(' ')} />;
}
