import type { ComponentPropsWithoutRef } from "react";
import styles from "./BaseTableRow.module.css";

export type BaseTableRowProps = ComponentPropsWithoutRef<"tr">;

export function BaseTableRow({ className, ...props }: BaseTableRowProps) {
  return (
    <tr
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    />
  );
}
