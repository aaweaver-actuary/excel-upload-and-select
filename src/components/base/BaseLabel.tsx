import type { ComponentPropsWithoutRef } from "react";

export type BaseLabelProps = ComponentPropsWithoutRef<"label">;

export function BaseLabel({ children, htmlFor, ...props }: BaseLabelProps) {
  return (
    <label {...props} htmlFor={htmlFor}>
      {children}
    </label>
  );
}
