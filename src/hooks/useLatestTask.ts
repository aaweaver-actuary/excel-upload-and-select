import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../api";

type Commit = (action: () => void) => void;

export function useLatestTask() {
  const generation = useRef(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(
    () => () => {
      generation.current += 1;
    },
    [],
  );

  async function run(operation: (commit: Commit) => Promise<void>) {
    const ticket = ++generation.current;
    setBusy(true);
    setError("");
    const commit: Commit = (action) => {
      if (ticket === generation.current) action();
    };
    try {
      await operation(commit);
    } catch (failure) {
      commit(() => setError(errorMessage(failure)));
    } finally {
      commit(() => setBusy(false));
    }
  }

  return { busy, error, run, clearError: () => setError("") };
}
