import { BaseButton } from "../base/BaseButton";
import { ErrorMessage } from "../shared/ErrorMessage";
import { StatusMessage } from "../shared/StatusMessage";

export interface ImportFeedbackProps {
  busy: boolean;
  error: string;
  canRetryMatching: boolean;
  onRetryMatching: () => void;
}

export function ImportFeedback({
  busy,
  error,
  canRetryMatching,
  onRetryMatching,
}: ImportFeedbackProps) {
  return (
    <>
      {busy && <StatusMessage>Working…</StatusMessage>}
      {error && <ErrorMessage>{error}</ErrorMessage>}
      {error && canRetryMatching && (
        <BaseButton onClick={onRetryMatching} disabled={busy}>
          Retry column matching
        </BaseButton>
      )}
    </>
  );
}
