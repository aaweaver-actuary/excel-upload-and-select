import type { ComponentPropsWithoutRef } from 'react';

export type BaseSpanProps = ComponentPropsWithoutRef<'span'>;

export function BaseSpan(props: BaseSpanProps) {
  return <span {...props} />;
}
