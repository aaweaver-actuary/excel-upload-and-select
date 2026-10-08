import type { ComponentPropsWithoutRef } from 'react';

export type BaseLinkProps = ComponentPropsWithoutRef<'a'>;

export function BaseLink(props: BaseLinkProps) {
  return <a {...props} />;
}
