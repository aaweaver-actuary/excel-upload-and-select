import type { ComponentPropsWithoutRef } from 'react';

export type BaseSectionProps = ComponentPropsWithoutRef<'section'>;

export function BaseSection(props: BaseSectionProps) {
  return <section {...props} />;
}
