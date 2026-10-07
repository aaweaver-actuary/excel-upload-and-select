import { useEffect, useState } from 'react';
import { errorMessage, getJob } from './api';
import type { BatchJob } from './types';

export function JobProgress({ initial }: { initial: BatchJob }) {
  const [job, setJob] = useState(initial);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const current = await getJob(initial.job_id);
        if (!active) return;
        setJob(current);
        setError('');
        if (current.status === 'queued' || current.status === 'running') timer = setTimeout(() => void poll(), 2000);
      } catch (failure) {
        if (active) setError(errorMessage(failure));
      }
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [initial.job_id, retry]);
  const complete = job.status === 'completed' || job.status === 'completed_with_issues';
  return <section className="preview-section">
    <h2>Batch processing</h2>
    <p role="status">{job.status}{job.stage ? ` · ${job.stage}` : ''}</p>
    <p>Job ID: {job.job_id}</p>
    {job.total_rows !== undefined && <p>{job.processed_rows ?? 0} of {job.total_rows} rows processed; {job.scored_rows ?? 0} scored; {job.needs_review_rows ?? 0} need review; {job.invalid_rows ?? 0} invalid.</p>}
    {error && <><p role="alert">{error}</p><button onClick={() => setRetry(value => value + 1)}>Retry status check</button></>}
    {job.status === 'failed' && <p role="alert">{job.error_message || 'Processing failed.'}</p>}
    {complete && <a href={`/api/v1/jobs/${encodeURIComponent(job.job_id)}/result`}>Download result workbook</a>}
  </section>;
}
