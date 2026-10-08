import type { ComponentPropsWithoutRef } from 'react';

export type BaseOptionProps = ComponentPropsWithoutRef<'option'>;

export function BaseOption(props: BaseOptionProps) {
  return <option {...props} />;
}
