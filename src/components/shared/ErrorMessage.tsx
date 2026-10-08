import { BaseParagraph } from '../base/BaseParagraph';
import type { BaseParagraphProps } from '../base/BaseParagraph';
import styles from './ErrorMessage.module.css';

export type ErrorMessageProps = BaseParagraphProps & {
  appearance?: 'boxed' | 'plain';
};

export function ErrorMessage({ appearance = 'boxed', className, ...props }: ErrorMessageProps) {
  return <BaseParagraph role="alert" {...props} className={[styles[appearance], className].filter(Boolean).join(' ')} />;
}
