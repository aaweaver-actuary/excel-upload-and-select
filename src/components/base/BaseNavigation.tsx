import type { ComponentPropsWithoutRef } from "react";

export type BaseNavigationProps = ComponentPropsWithoutRef<"nav">;

export function BaseNavigation(props: BaseNavigationProps) {
  return <nav {...props} />;
}
