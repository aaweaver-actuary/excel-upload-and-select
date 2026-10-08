import { useEffect, useState } from "react";
import { errorMessage, getJob } from "../api";
import type { BatchJob } from "../types";

export function useJobProgress(initial: BatchJob) {
  const [job, setJob] = useState(initial);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const current = await getJob(initial.job_id);
        if (!active) return;
        setJob(current);
        setError("");
        if (current.status === "queued" || current.status === "running")
          timer = setTimeout(() => void poll(), 2000);
      } catch (failure) {
        if (active) setError(errorMessage(failure));
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [initial.job_id, retry]);

  const complete =
    job.status === "completed" || job.status === "completed_with_issues";
  function retryStatus() {
    setRetry((value) => value + 1);
  }
  return { job, error, complete, retryStatus };
}
