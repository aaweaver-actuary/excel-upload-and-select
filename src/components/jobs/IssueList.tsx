import { BaseParagraph } from "../base/BaseParagraph";
import { BaseList } from "../base/BaseList";
import { BaseListItem } from "../base/BaseListItem";
import { BaseCode } from "../base/BaseCode";
import { readable } from "./resultFormatting";

const explanations: Record<string, string> = {
  SCORING_NOT_CONFIGURED: "No scoring model is configured for this run.",
  NAICS_PROVIDER_NOT_CONFIGURED:
    "No NAICS provider is configured to resolve missing or invalid codes.",
  NAICS_REFERENCE_NOT_CONFIGURED:
    "No NAICS reference dataset is configured. This code is unverified.",
  MISSING_BUSINESS_NAME: "A business name is required to process this row.",
};

export function IssueList({ codes }: { codes: string[] }) {
  return codes.length === 0 ? (
    <BaseParagraph>No issues.</BaseParagraph>
  ) : (
    <BaseList>
      {codes.map((code) => (
        <BaseListItem key={code}>
          {explanations[code] ?? readable(code)} <BaseCode>({code})</BaseCode>
        </BaseListItem>
      ))}
    </BaseList>
  );
}
