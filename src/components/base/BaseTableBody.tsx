import type { ComponentPropsWithoutRef } from 'react';

export type BaseTableBodyProps = ComponentPropsWithoutRef<'tbody'>;

export function BaseTableBody(props: BaseTableBodyProps) {
  return <tbody {...props} />;
}
