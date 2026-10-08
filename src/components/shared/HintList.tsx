import { BaseList } from "../base/BaseList";
import type { BaseListProps } from "../base/BaseList";
import styles from "./HintList.module.css";

export function HintList({ className, ...props }: BaseListProps) {
  return (
    <BaseList
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    />
  );
}
