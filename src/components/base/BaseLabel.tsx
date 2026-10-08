import type { ComponentPropsWithoutRef } from "react";

export type BaseLabelProps = ComponentPropsWithoutRef<"label">;

export function BaseLabel(props: BaseLabelProps) {
  return <label {...props} />;
}
