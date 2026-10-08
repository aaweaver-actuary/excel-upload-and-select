import type { ReactNode } from 'react';
import { BaseDetails } from '../base/BaseDetails';
import type { BaseDetailsProps } from '../base/BaseDetails';
import { BaseSummary } from '../base/BaseSummary';

export type DisclosureProps = BaseDetailsProps & {
  summary: ReactNode;
};

export function Disclosure({ summary, children, ...props }: DisclosureProps) {
  return <BaseDetails {...props}><BaseSummary>{summary}</BaseSummary>{children}</BaseDetails>;
}
