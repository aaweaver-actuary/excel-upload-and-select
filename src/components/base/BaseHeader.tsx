import type { ComponentPropsWithoutRef } from "react";
import styles from "./BaseHeader.module.css";

export type BaseHeaderProps = ComponentPropsWithoutRef<"h1">;

export function BaseHeader({ children, className, ...props }: BaseHeaderProps) {
  return (
    <h1
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    >
      {children}
    </h1>
  );
}
