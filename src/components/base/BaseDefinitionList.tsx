import type { ComponentPropsWithoutRef } from 'react';

export type BaseDefinitionListProps = ComponentPropsWithoutRef<'dl'>;

export function BaseDefinitionList(props: BaseDefinitionListProps) {
  return <dl {...props} />;
}
