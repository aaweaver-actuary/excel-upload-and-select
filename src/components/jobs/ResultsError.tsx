import { BaseButton } from "../base/BaseButton";
import { ErrorMessage } from "../shared/ErrorMessage";

export function ResultsError({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return (
    <>
      <ErrorMessage appearance="plain">{error}</ErrorMessage>
      <BaseButton onClick={onRetry}>Retry results</BaseButton>
    </>
  );
}
