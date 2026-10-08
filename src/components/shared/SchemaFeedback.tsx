import { BaseButton } from "../base/BaseButton";
import { ErrorMessage } from "./ErrorMessage";
import { StatusMessage } from "./StatusMessage";

export function SchemaFeedback({
  busy,
  error,
  onRetry,
}: {
  busy: boolean;
  error: string;
  onRetry: () => void;
}) {
  return (
    <>
      {busy && <StatusMessage>Loading column definitions…</StatusMessage>}
      {error && (
        <>
          <ErrorMessage>{error}</ErrorMessage>
          <BaseButton onClick={onRetry}>Retry connection</BaseButton>
        </>
      )}
    </>
  );
}
