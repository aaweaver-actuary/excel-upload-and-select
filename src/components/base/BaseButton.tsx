import type { ComponentPropsWithoutRef } from "react";
import styles from "./BaseButton.module.css";

export type BaseButtonProps = ComponentPropsWithoutRef<"button"> & {
  variant?: "default" | "primary";
};

export function BaseButton({
  className,
  variant = "default",
  ...props
}: BaseButtonProps) {
  return (
    <button
      {...props}
      className={[styles.element, styles[variant], className]
        .filter(Boolean)
        .join(" ")}
    />
  );
}
