import { BaseMain } from "../base/BaseMain";
import type { BaseMainProps } from "../base/BaseMain";
import styles from "./Panel.module.css";

export function Panel({ className, ...props }: BaseMainProps) {
  return (
    <BaseMain
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    />
  );
}
