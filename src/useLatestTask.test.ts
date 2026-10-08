import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useLatestTask } from "./hooks/useLatestTask";
import { deferred } from "./test/fixtures";

describe("latest task coordination", () => {
  it("commits only the latest operation and clears errors on retry", async () => {
    const { result } = renderHook(useLatestTask);
    await act(async () =>
      result.current.run(async () => {
        throw null;
      }),
    );
    expect(result.current.error).toContain("Please try again");
    act(() => result.current.clearError());
    expect(result.current.error).toBe("");
    const old = deferred<void>();
    const commit = vi.fn();
    let running: Promise<void>;
    act(() => {
      running = result.current.run(async (apply) => {
        await old.promise;
        apply(commit);
      });
    });
    expect(result.current.busy).toBe(true);
    await act(async () => result.current.run(async (apply) => apply(commit)));
    await act(async () => {
      old.resolve();
      await running;
    });
    expect(commit).toHaveBeenCalledTimes(1);
    expect(result.current.busy).toBe(false);
  });

  it("does not commit after unmounting", async () => {
    const { result, unmount } = renderHook(useLatestTask);
    const pending = deferred<void>();
    const commit = vi.fn();
    let running: Promise<void>;
    act(() => {
      running = result.current.run(async (apply) => {
        await pending.promise;
        apply(commit);
      });
    });
    unmount();
    await act(async () => {
      pending.resolve();
      await running;
    });
    expect(commit).not.toHaveBeenCalled();
  });
});
