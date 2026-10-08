import type { ComponentPropsWithoutRef } from 'react';

export type BaseListProps = ComponentPropsWithoutRef<'ul'>;

export function BaseList(props: BaseListProps) {
  return <ul {...props} />;
}
