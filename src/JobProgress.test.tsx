import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { JobProgress } from "./components/jobs/JobProgress";
import { completedJob, deferred, response } from "./test/fixtures";

let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>;
beforeEach(() => {
  fetch = vi.fn<typeof globalThis.fetch>();
  vi.stubGlobal("fetch", fetch);
  vi.useFakeTimers();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("polls queued and running jobs until a terminal result is downloadable", async () => {
  fetch
    .mockResolvedValueOnce(
      response({ job_id: "id", status: "queued", total_rows: 12 }),
    )
    .mockResolvedValueOnce(
      response({
        job_id: "id",
        status: "running",
        stage: "enrichment",
        total_rows: 12,
      }),
    )
    .mockResolvedValueOnce(response({ ...completedJob, status: "completed" }))
    .mockResolvedValueOnce(response({ total: 0, rows: [], limit: 50 }));
  await act(async () => {
    render(<JobProgress initial={{ job_id: "id", status: "queued" }} />);
  });
  expect(screen.getByText(/0 of 12 rows processed/)).toBeInTheDocument();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(screen.getByRole("status")).toHaveTextContent("running · enrichment");
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(screen.getByRole("link")).toBeInTheDocument();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(4000);
  });
  expect(fetch).toHaveBeenCalledTimes(4);
});

it.each([null, "The workbook failed."])(
  "shows terminal failures without a download link",
  async (message) => {
    fetch.mockResolvedValue(
      response({ job_id: "id", status: "failed", error_message: message }),
    );
    await act(async () => {
      render(<JobProgress initial={{ job_id: "id", status: "queued" }} />);
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      message || "Processing failed.",
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  },
);

it("retries a failed status request without resubmitting a job", async () => {
  fetch
    .mockRejectedValueOnce(new Error("Offline"))
    .mockResolvedValueOnce(response(completedJob))
    .mockResolvedValueOnce(response({ total: 0, rows: [], limit: 50 }));
  await act(async () => {
    render(<JobProgress initial={{ job_id: "id", status: "queued" }} />);
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Offline");
  await act(async () => {
    fireEvent.click(screen.getByText("Retry status check"));
  });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.getByRole("link")).toBeInTheDocument();
});

it.each(["resolve", "reject"])(
  "ignores stale %s responses after unmount",
  async (action) => {
    const pending = deferred<Response>();
    fetch.mockImplementation(() => pending.promise);
    const view = render(
      <JobProgress initial={{ job_id: "old", status: "queued" }} />,
    );
    view.unmount();
    await act(async () => {
      if (action === "resolve") pending.resolve(response(completedJob));
      else pending.reject(new Error("Old failure"));
    });
    expect(vi.getTimerCount()).toBe(0);
  },
);
