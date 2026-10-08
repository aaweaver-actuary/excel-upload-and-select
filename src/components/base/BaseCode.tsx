import type { ComponentPropsWithoutRef } from "react";

export type BaseCodeProps = ComponentPropsWithoutRef<"code">;

export function BaseCode(props: BaseCodeProps) {
  return <code {...props} />;
}
