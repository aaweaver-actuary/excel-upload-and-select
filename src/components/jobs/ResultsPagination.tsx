import { BaseNavigation } from '../base/BaseNavigation';
import { BaseButton } from '../base/BaseButton';
import { BaseSpan } from '../base/BaseSpan';
import styles from './ResultsPagination.module.css';

export interface ResultsPaginationProps {
  offset: number;
  total: number;
  count: number;
  limit: number;
  onPrevious: () => void;
  onNext: () => void;
}

export function ResultsPagination({ offset, total, count, limit, onPrevious, onNext }: ResultsPaginationProps) {
  return <BaseNavigation className={styles.navigation} aria-label="Results pages">
    <BaseButton disabled={offset === 0} onClick={onPrevious}>Previous</BaseButton>
    <BaseSpan>{total === 0 ? '0 rows' : `${Math.min(offset + 1, total)}–${Math.min(offset + count, total)} of ${total} rows`}</BaseSpan>
    <BaseButton disabled={offset + limit >= total} onClick={onNext}>Next</BaseButton>
  </BaseNavigation>;
}
