import { BaseSpan } from "../base/BaseSpan";
import type { BaseSpanProps } from "../base/BaseSpan";
import styles from "./HintSpan.module.css";

export function HintSpan({ className, ...props }: BaseSpanProps) {
  return (
    <BaseSpan
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    />
  );
}
