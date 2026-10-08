import type { RowResult } from "../../types";
import { BaseDetailHeader } from "../base/BaseDetailHeader";
import { Disclosure } from "../shared/Disclosure";
import { NormalizedInputs } from "./NormalizedInputs";
import { NaicsDetails } from "./NaicsDetails";
import { ScoreDetails } from "./ScoreDetails";
import { IssueList } from "./IssueList";

export function RowDetails({ row }: { row: RowResult }) {
  return (
    <Disclosure summary={`Details for row ${row.source_row_number}`}>
      <NormalizedInputs account={row.canonical_account} />
      <BaseDetailHeader>Row issues</BaseDetailHeader>
      <IssueList codes={row.issues} />
      <NaicsDetails naics={row.naics} />
      {Object.entries(row.scores).map(([name, score]) => (
        <ScoreDetails key={name} name={name} score={score} />
      ))}
    </Disclosure>
  );
}
