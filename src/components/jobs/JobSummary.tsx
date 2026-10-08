import type { BatchJob } from '../../types';
import { BaseParagraph } from '../base/BaseParagraph';
import { StatusMessage } from '../shared/StatusMessage';

export function JobSummary({ job }: { job: BatchJob }) {
  return <>
    <StatusMessage>{job.status}{job.stage ? ` · ${job.stage}` : ''}</StatusMessage>
    <BaseParagraph>Job ID: {job.job_id}</BaseParagraph>
    {job.total_rows !== undefined && <BaseParagraph>{job.processed_rows ?? 0} of {job.total_rows} rows processed; {job.scored_rows ?? 0} scored; {job.needs_review_rows ?? 0} need review; {job.invalid_rows ?? 0} invalid.</BaseParagraph>}
  </>;
}
