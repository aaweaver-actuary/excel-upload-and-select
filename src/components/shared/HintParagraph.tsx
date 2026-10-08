import { BaseParagraph } from "../base/BaseParagraph";
import type { BaseParagraphProps } from "../base/BaseParagraph";
import styles from "./HintParagraph.module.css";

export function HintParagraph({ className, ...props }: BaseParagraphProps) {
  return (
    <BaseParagraph
      {...props}
      className={[styles.element, className].filter(Boolean).join(" ")}
    />
  );
}
