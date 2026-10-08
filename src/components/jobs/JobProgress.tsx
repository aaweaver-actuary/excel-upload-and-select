import { useJobProgress } from '../../hooks/useJobProgress';
import type { BatchJob } from '../../types';
import { BaseSubheader } from '../base/BaseSubheader';
import { Section } from '../layout/Section';
import { JobSummary } from './JobSummary';
import { JobFeedback } from './JobFeedback';
import { ResultDownloadLink } from './ResultDownloadLink';
import { JobResults } from './JobResults';

export function JobProgress({ initial }: { initial: BatchJob }) {
  const { job, error, complete, retryStatus } = useJobProgress(initial);
  return <Section>
    <BaseSubheader>Batch processing</BaseSubheader>
    <JobSummary job={job} />
    <JobFeedback job={job} error={error} onRetry={retryStatus} />
    {complete && <ResultDownloadLink jobId={job.job_id} />}
    {complete && <JobResults key={job.job_id} job={job} />}
  </Section>;
}
