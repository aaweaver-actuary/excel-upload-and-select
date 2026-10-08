import type { ComponentPropsWithoutRef } from 'react';

export type BaseDetailHeaderProps = ComponentPropsWithoutRef<'h3'>;

export function BaseDetailHeader(props: BaseDetailHeaderProps) {
  return <h3 {...props} />;
}
