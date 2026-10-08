import type { ComponentPropsWithoutRef } from "react";

export type BaseTableHeadProps = ComponentPropsWithoutRef<"thead">;

export function BaseTableHead(props: BaseTableHeadProps) {
  return <thead {...props} />;
}
