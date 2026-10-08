import type { ComponentPropsWithoutRef } from "react";
import styles from "./BaseSubheader.module.css";

export type BaseSubheaderProps = ComponentPropsWithoutRef<"h2">;

export function BaseSubheader({
  children,
  className,
  ...props
}: BaseSubheaderProps) {
  return (
    <h2
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    >
      {children}
    </h2>
  );
}
