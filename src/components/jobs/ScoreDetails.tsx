import type { RowResult } from "../../types";
import { BaseContainer } from "../base/BaseContainer";
import { BaseDetailHeader } from "../base/BaseDetailHeader";
import { BaseParagraph } from "../base/BaseParagraph";
import { IssueList } from "./IssueList";
import { display, readable } from "./resultFormatting";

export function ScoreDetails({
  name,
  score,
}: {
  name: string;
  score: RowResult["scores"][string];
}) {
  return (
    <BaseContainer>
      <BaseDetailHeader>{name}</BaseDetailHeader>
      <BaseParagraph>
        Value: {display(score.value)} · Status: {readable(score.status)}
      </BaseParagraph>
      <IssueList codes={score.issues} />
    </BaseContainer>
  );
}
