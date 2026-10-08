import type { CellValue, RowResult } from "../../types";
import { BaseDetailHeader } from "../base/BaseDetailHeader";
import { DefinitionList } from "../shared/DefinitionList";
import { IssueList } from "./IssueList";
import { display, readable } from "./resultFormatting";

export function NaicsDetails({ naics }: { naics: RowResult["naics"] }) {
  return (
    <>
      <BaseDetailHeader>NAICS resolution</BaseDetailHeader>
      <DefinitionList
        items={Object.entries(naics)
          .filter(([field]) => field !== "warning_codes")
          .map(([field, value]) => ({
            key: field,
            label: readable(field),
            value: display(value as CellValue),
          }))}
      />
      <IssueList codes={naics.warning_codes} />
    </>
  );
}
