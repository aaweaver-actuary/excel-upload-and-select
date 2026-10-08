import { useEffect, useState } from 'react';
import { errorMessage, getJobRows } from '../api';
import type { BatchJob, JobRows, RowStatus } from '../types';

export function useJobResults(job: BatchJob) {
  const [status, setStatus] = useState<RowStatus | ''>('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<JobRows | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');
    void getJobRows(job.job_id, offset, status).then(result => {
      if (active) setData(result);
    }).catch(failure => {
      if (active) setError(errorMessage(failure));
    });
    return () => { active = false; };
  }, [job.job_id, offset, status, retry]);

  const scorerNames = [...new Set([...Object.keys(job.versions?.scorers ?? {}),
    ...data?.rows.flatMap(row => Object.keys(row.scores)) ?? []])];

  function selectStatus(value: RowStatus | '') {
    setStatus(value);
    setOffset(0);
  }
  function previousPage() {
    setOffset(value => value - 50);
  }
  function nextPage() {
    setOffset(value => value + 50);
  }
  function retryResults() {
    setRetry(value => value + 1);
  }

  return { status, offset, data, error, scorerNames, selectStatus, previousPage, nextPage, retryResults };
}
