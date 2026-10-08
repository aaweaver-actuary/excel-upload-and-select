import { useJobResults } from "../../hooks/useJobResults";
import type { BatchJob } from "../../types";
import { BaseSubheader } from "../base/BaseSubheader";
import { Section } from "../layout/Section";
import { ProcessingVersions } from "./ProcessingVersions";
import { ResultsFilter } from "./ResultsFilter";
import { ResultsError } from "./ResultsError";
import { ResultsLoading } from "./ResultsLoading";
import { EmptyResults } from "./EmptyResults";
import { ResultsTable } from "./ResultsTable";
import { ResultsPagination } from "./ResultsPagination";

export function JobResults({ job }: { job: BatchJob }) {
  const state = useJobResults(job);
  return (
    <Section aria-label="Processing results">
      <BaseSubheader>Processing results</BaseSubheader>
      {job.versions && <ProcessingVersions versions={job.versions} />}
      <ResultsFilter status={state.status} onSelect={state.selectStatus} />
      {state.error ? (
        <ResultsError error={state.error} onRetry={state.retryResults} />
      ) : state.data === null ? (
        <ResultsLoading />
      ) : (
        <>
          {state.data.rows.length === 0 ? (
            <EmptyResults />
          ) : (
            <ResultsTable
              rows={state.data.rows}
              scorerNames={state.scorerNames}
            />
          )}
          <ResultsPagination
            offset={state.offset}
            total={state.data.total}
            count={state.data.rows.length}
            limit={state.data.limit}
            onPrevious={state.previousPage}
            onNext={state.nextPage}
          />
        </>
      )}
    </Section>
  );
}
