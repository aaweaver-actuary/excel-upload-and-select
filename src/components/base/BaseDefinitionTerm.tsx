import type { ComponentPropsWithoutRef } from 'react';

export type BaseDefinitionTermProps = ComponentPropsWithoutRef<'dt'>;

export function BaseDefinitionTerm(props: BaseDefinitionTermProps) {
  return <dt {...props} />;
}
