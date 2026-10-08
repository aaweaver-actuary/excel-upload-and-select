import type { ComponentPropsWithoutRef } from 'react';

export type BaseStrongProps = ComponentPropsWithoutRef<'strong'>;

export function BaseStrong(props: BaseStrongProps) {
  return <strong {...props} />;
}
