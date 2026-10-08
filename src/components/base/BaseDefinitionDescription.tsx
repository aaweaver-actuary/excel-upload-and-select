import type { ComponentPropsWithoutRef } from "react";

export type BaseDefinitionDescriptionProps = ComponentPropsWithoutRef<"dd">;

export function BaseDefinitionDescription(
  props: BaseDefinitionDescriptionProps,
) {
  return <dd {...props} />;
}
