import type { BatchJob } from "../../types";
import { BaseButton } from "../base/BaseButton";
import { ErrorMessage } from "../shared/ErrorMessage";

export function JobFeedback({
  job,
  error,
  onRetry,
}: {
  job: BatchJob;
  error: string;
  onRetry: () => void;
}) {
  return (
    <>
      {error && (
        <>
          <ErrorMessage appearance="plain">{error}</ErrorMessage>
          <BaseButton onClick={onRetry}>Retry status check</BaseButton>
        </>
      )}
      {job.status === "failed" && (
        <ErrorMessage appearance="plain">
          {job.error_message || "Processing failed."}
        </ErrorMessage>
      )}
    </>
  );
}
