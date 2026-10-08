import type { ComponentPropsWithoutRef } from 'react';

export type BaseParagraphProps = ComponentPropsWithoutRef<'p'>;

export function BaseParagraph(props: BaseParagraphProps) {
  return <p {...props} />;
}
