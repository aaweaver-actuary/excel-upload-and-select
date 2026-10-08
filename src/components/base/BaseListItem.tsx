import type { ComponentPropsWithoutRef } from "react";

export type BaseListItemProps = ComponentPropsWithoutRef<"li">;

export function BaseListItem(props: BaseListItemProps) {
  return <li {...props} />;
}
