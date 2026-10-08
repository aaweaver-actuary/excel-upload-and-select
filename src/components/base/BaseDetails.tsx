import type { ComponentPropsWithoutRef } from "react";

export type BaseDetailsProps = ComponentPropsWithoutRef<"details">;

export function BaseDetails(props: BaseDetailsProps) {
  return <details {...props} />;
}
