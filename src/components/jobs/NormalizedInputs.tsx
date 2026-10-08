import type { CanonicalAccount } from "../../types";
import { BaseDetailHeader } from "../base/BaseDetailHeader";
import { BaseParagraph } from "../base/BaseParagraph";
import { DefinitionList } from "../shared/DefinitionList";
import { display, readable } from "./resultFormatting";

export function NormalizedInputs({
  account,
}: {
  account: CanonicalAccount | null;
}) {
  return (
    <>
      <BaseDetailHeader>Normalized inputs</BaseDetailHeader>
      {account === null ? (
        <BaseParagraph>
          Normalized inputs are unavailable for this older result.
        </BaseParagraph>
      ) : (
        <DefinitionList
          items={Object.entries(account).map(([field, value]) => ({
            key: field,
            label: readable(field),
            value: display(value),
          }))}
        />
      )}
    </>
  );
}
