import type { ComponentPropsWithoutRef } from "react";

export type BaseLinkProps = ComponentPropsWithoutRef<"a">;

export function BaseLink({ children, ...props }: BaseLinkProps) {
  return <a {...props}>{children}</a>;
}
