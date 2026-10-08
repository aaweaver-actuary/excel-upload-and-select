import { useEffect, useState } from "react";
import { errorMessage, getJobRows } from "../api";
import type { BatchJob, JobRows, RowStatus } from "../types";

export function useJobResults(job: BatchJob) {
  const [status, setStatus] = useState<RowStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [response, setResponse] = useState<{
    requestKey: string;
    data: JobRows | null;
    error: string;
  } | null>(null);
  const requestKey = JSON.stringify([job.job_id, offset, status, retry]);
  const [selectionKey, setSelectionKey] = useState(requestKey);
  if (selectionKey !== requestKey) {
    // Reset during render so returning to an earlier selection cannot reuse its
    // old response while the new request is pending.
    setSelectionKey(requestKey);
    setResponse(null);
  }
  // Hide results from a previous request as soon as the selection changes.
  const current = response?.requestKey === requestKey ? response : null;
  const data = current?.data ?? null;
  const error = current?.error ?? "";

  useEffect(() => {
    let active = true;
    void getJobRows(job.job_id, offset, status)
      .then((result) => {
        if (active) setResponse({ requestKey, data: result, error: "" });
      })
      .catch((failure: unknown) => {
        if (active)
          setResponse({ requestKey, data: null, error: errorMessage(failure) });
      });
    return () => {
      active = false;
    };
  }, [job.job_id, offset, status, requestKey]);

  const scorerNames = [
    ...new Set([
      ...Object.keys(job.versions?.scorers ?? {}),
      ...(data?.rows.flatMap((row) => Object.keys(row.scores)) ?? []),
    ]),
  ];

  function selectStatus(value: RowStatus | "") {
    setStatus(value);
    setOffset(0);
  }
  function previousPage() {
    setOffset((value) => value - 50);
  }
  function nextPage() {
    setOffset((value) => value + 50);
  }
  function retryResults() {
    setRetry((value) => value + 1);
  }

  return {
    status,
    offset,
    data,
    error,
    scorerNames,
    selectStatus,
    previousPage,
    nextPage,
    retryResults,
  };
}
