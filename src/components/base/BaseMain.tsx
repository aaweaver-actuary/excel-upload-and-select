import type { ComponentPropsWithoutRef } from "react";

export type BaseMainProps = ComponentPropsWithoutRef<"main">;

export function BaseMain(props: BaseMainProps) {
  return <main {...props} />;
}
