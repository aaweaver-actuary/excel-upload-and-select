import type { ComponentPropsWithoutRef } from "react";

export type BaseContainerProps = ComponentPropsWithoutRef<"div">;

export function BaseContainer(props: BaseContainerProps) {
  return <div {...props} />;
}
