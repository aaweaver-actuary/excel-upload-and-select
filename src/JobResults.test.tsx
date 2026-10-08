import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { JobResults } from "./components/jobs/JobResults";
import type { BatchJob, JobRows, RowResult } from "./types";
import { completedJob, deferred, response } from "./test/fixtures";

let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>;
beforeEach(() => {
  fetch = vi.fn<typeof globalThis.fetch>();
  vi.stubGlobal("fetch", fetch);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const versions: NonNullable<BatchJob["versions"]> = {
  pipeline: "test-1",
  provider: "none",
  provider_version: "unconfigured",
  naics_reference: "unconfigured",
  reference_data: "unconfigured",
  scorers: { Zero: "v1", Missing: "v2" },
};
function row(overrides: Partial<RowResult> = {}): RowResult {
  return {
    source_row_number: 2,
    status: "needs_review",
    canonical_account: {
      source_row_number: 2,
      business_name: "Alpha",
      account_id: "0001",
      address_line_1: null,
      address_line_2: null,
      city: null,
      state: "NY",
      postal_code: "00123",
      naics: "541330",
    },
    issues: [
      "SCORING_NOT_CONFIGURED",
      "NAICS_PROVIDER_NOT_CONFIGURED",
      "NAICS_REFERENCE_NOT_CONFIGURED",
      "MISSING_BUSINESS_NAME",
      "INVALID_POSTAL_CODE",
    ],
    naics: {
      input_value: "541330.0",
      final_value: "541330",
      source: "submitted",
      status: "unverified",
      provider: null,
      provider_record_id: null,
      provider_confidence: 0,
      retrieved_at: null,
      warning_codes: ["NAICS_REFERENCE_NOT_CONFIGURED"],
    },
    scores: {
      Zero: { value: 0, status: "scored", issues: [] },
      Broken: { value: null, status: "model_error", issues: ["MODEL_ERROR"] },
    },
    ...overrides,
  };
}
function page(rows = [row()], overrides: Partial<JobRows> = {}): JobRows {
  return {
    job_id: completedJob.job_id,
    offset: 0,
    limit: 50,
    total: rows.length,
    rows,
    ...overrides,
  };
}
async function show(job: BatchJob = { ...completedJob, versions }) {
  await act(async () => {
    render(<JobResults job={job} />);
  });
}

it("shows backend values, versions, dynamic scorers and full row details without treating zero as missing", async () => {
  fetch.mockResolvedValue(response(page()));
  await show();
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/jobs/job-1/rows?offset=0&limit=50",
  );
  expect(screen.getByText("test-1")).toBeInTheDocument();
  expect(screen.getByText("v1")).toBeInTheDocument();
  expect(
    screen.getByRole("columnheader", { name: "Broken · value / status" }),
  ).toBeInTheDocument();
  expect(screen.getByText("0 · scored")).toBeInTheDocument();
  expect(screen.getByText("— · not scored")).toBeInTheDocument();
  const details = screen.getByText("Details for row 2").parentElement!;
  fireEvent.click(screen.getByText("Details for row 2"));
  expect(within(details).getByText("0001")).toBeInTheDocument();
  expect(within(details).getByText("00123")).toBeInTheDocument();
  expect(
    within(details).getByText(/No scoring model is configured/),
  ).toBeInTheDocument();
  expect(
    within(details).getByText(/No NAICS provider is configured/),
  ).toBeInTheDocument();
  expect(within(details).getAllByText(/This code is unverified/)).toHaveLength(
    2,
  );
  expect(
    within(details).getByText(/A business name is required/),
  ).toBeInTheDocument();
  expect(within(details).getByText(/invalid postal code/)).toBeInTheDocument();
  expect(within(details).getAllByText(/model error/)).toHaveLength(2);
  expect(within(details).getByText("No issues.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});

it("supports older results, no scorers, missing values and literal false inputs", async () => {
  const legacy = row({ canonical_account: null, issues: [], scores: {} });
  legacy.naics = {
    ...legacy.naics,
    input_value: false,
    final_value: null,
    warning_codes: [],
  };
  fetch.mockResolvedValue(response(page([legacy])));
  await show(completedJob);
  expect(screen.queryByText("Processing versions")).not.toBeInTheDocument();
  expect(screen.getAllByText("false")).toHaveLength(2);
  expect(
    screen.getByText(/Normalized inputs are unavailable/),
  ).toBeInTheDocument();
  expect(screen.getAllByText("No issues.")).toHaveLength(2);
});

it("paginates, resets pagination on filtering and supports all row-status filters", async () => {
  fetch
    .mockResolvedValueOnce(response(page([row()], { total: 101 })))
    .mockResolvedValueOnce(
      response(
        page([row({ source_row_number: 52 })], { offset: 50, total: 101 }),
      ),
    )
    .mockResolvedValueOnce(response(page([row()], { total: 101 })))
    .mockResolvedValueOnce(
      response(
        page([row({ source_row_number: 52 })], { offset: 50, total: 101 }),
      ),
    )
    .mockImplementation(() => Promise.resolve(response(page([]))));
  await show();
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
  });
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/jobs/job-1/rows?offset=50&limit=50",
  );
  expect(screen.getByText("51–51 of 101 rows")).toBeInTheDocument();
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
  });
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/jobs/job-1/rows?offset=0&limit=50",
  );
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
  });
  for (const status of [
    "needs_review",
    "invalid",
    "scored_with_warnings",
    "scored",
    "",
  ]) {
    await act(async () => {
      fireEvent.change(screen.getByLabelText("Row status"), {
        target: { value: status },
      });
    });
    expect(fetch).toHaveBeenLastCalledWith(
      `/api/v1/jobs/job-1/rows?offset=0&limit=50${status ? `&status=${status}` : ""}`,
    );
  }
  expect(screen.getByText("No rows match this filter.")).toBeInTheDocument();
  expect(screen.getByText("0 rows")).toBeInTheDocument();
});

it("shows loading and retries a failed result request without processing again", async () => {
  const pending = deferred<Response>();
  fetch
    .mockReturnValueOnce(pending.promise)
    .mockResolvedValueOnce(response(page()));
  await show();
  expect(screen.getByText("Loading results…")).toBeInTheDocument();
  await act(async () => {
    pending.reject(new Error("Results offline"));
  });
  expect(screen.getByRole("alert")).toHaveTextContent("Results offline");
  await act(async () => {
    fireEvent.click(screen.getByText("Retry results"));
  });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("shows loading when returning to a previous filter while another request is pending", async () => {
  const oldFilter = deferred<Response>();
  const newRequest = deferred<Response>();
  fetch
    .mockResolvedValueOnce(response(page()))
    .mockReturnValueOnce(oldFilter.promise)
    .mockReturnValueOnce(newRequest.promise);
  await show();
  expect(screen.getByText("Details for row 2")).toBeInTheDocument();
  await act(async () => {
    fireEvent.change(screen.getByLabelText("Row status"), {
      target: { value: "invalid" },
    });
  });
  await act(async () => {
    fireEvent.change(screen.getByLabelText("Row status"), {
      target: { value: "" },
    });
  });
  expect(screen.getByText("Loading results…")).toBeInTheDocument();
  expect(screen.queryByText("Details for row 2")).not.toBeInTheDocument();
  await act(async () => {
    oldFilter.resolve(response(page([row({ source_row_number: 8 })])));
  });
  expect(screen.getByText("Loading results…")).toBeInTheDocument();
  await act(async () => {
    newRequest.resolve(response(page([row({ source_row_number: 9 })])));
  });
  expect(screen.getByText("Details for row 9")).toBeInTheDocument();
  expect(screen.queryByText("Details for row 8")).not.toBeInTheDocument();
});

it.each(["resolve", "reject"])(
  "ignores stale %s requests when changing job or filter",
  async (action) => {
    const pending = deferred<Response>();
    fetch
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValue(response(page([row({ source_row_number: 9 })])));
    const view = render(<JobResults job={completedJob} />);
    await act(async () => {
      view.rerender(<JobResults job={{ ...completedJob, job_id: "new/id" }} />);
    });
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/jobs/new%2Fid/rows?offset=0&limit=50",
    );
    await act(async () => {
      if (action === "resolve") pending.resolve(response(page()));
      else pending.reject(new Error("Stale error"));
    });
    expect(screen.queryByText("Details for row 2")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Details for row 9")).toBeInTheDocument();
    const oldFilter = deferred<Response>();
    fetch
      .mockReturnValueOnce(oldFilter.promise)
      .mockImplementation(() => Promise.resolve(response(page([]))));
    await act(async () => {
      fireEvent.change(screen.getByLabelText("Row status"), {
        target: { value: "invalid" },
      });
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText("Row status"), {
        target: { value: "scored" },
      });
    });
    await act(async () => {
      oldFilter.resolve(response(page()));
    });
    expect(screen.getByText("No rows match this filter.")).toBeInTheDocument();
  },
);

it.each(["resolve", "reject"])(
  "ignores stale %s requests on page changes and unmount",
  async (action) => {
    const pending = deferred<Response>();
    fetch
      .mockResolvedValueOnce(response(page([row()], { total: 101 })))
      .mockReturnValueOnce(pending.promise)
      .mockImplementation(() => Promise.resolve(response(page([]))));
    const view = render(<JobResults job={completedJob} />);
    await act(async () => {});
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
    });
    expect(screen.getByText("Loading results…")).toBeInTheDocument();
    expect(screen.queryByText("Details for row 2")).not.toBeInTheDocument();
    view.unmount();
    await act(async () => {
      if (action === "resolve") pending.resolve(response(page()));
      else pending.reject(new Error("Stale page"));
    });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  },
);
