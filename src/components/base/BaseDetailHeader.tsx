import type { ComponentPropsWithoutRef } from "react";

export type BaseDetailHeaderProps = ComponentPropsWithoutRef<"h3">;

export function BaseDetailHeader({
  children,
  ...props
}: BaseDetailHeaderProps) {
  return <h3 {...props}>{children}</h3>;
}
