import { describe, expect, it } from "vitest";
import { mappingIssues, needsApproval, suggestedMapping } from "./mapping";
import { exact, fuzzy, schema, suggestions } from "./test/fixtures";

describe("mapping rules", () => {
  it("starts with exact/fuzzy suggestions and leaves ambiguous and unmatched fields empty", () => {
    expect(suggestedMapping(fuzzy)).toEqual({
      firstName: "A",
      lastName: null,
      email: "B",
      phone: null,
      company: null,
      state: null,
    });
  });

  it("requires approval only for selected non-exact mappings", () => {
    expect(needsApproval(exact[0], "A", [])).toBe(false);
    expect(needsApproval(exact[0], "B", [])).toBe(true);
    expect(needsApproval(exact[0], "B", ["firstName"])).toBe(false);
    expect(needsApproval(fuzzy[2], null, [])).toBe(false);
    expect(needsApproval(fuzzy[2], "B", [])).toBe(true);
    expect(needsApproval(fuzzy[2], "B", ["email"])).toBe(false);
    expect(
      needsApproval({ ...fuzzy[2], matchType: "ambiguous" }, null, []),
    ).toBe(true);
    expect(
      needsApproval({ ...fuzzy[2], matchType: "ambiguous" }, null, ["email"]),
    ).toBe(false);
  });

  it("checks empty mappings, conflicts, approvals, and required fields", () => {
    expect(
      mappingIssues(schema, suggestions(), suggestedMapping(suggestions()), []),
    ).toEqual(["Map at least one field."]);
    expect(mappingIssues(schema, fuzzy, suggestedMapping(fuzzy), [])).toEqual([
      "Approve or change the suggested mappings before processing.",
    ]);
    expect(
      mappingIssues(schema, exact, { ...suggestedMapping(exact), email: "A" }, [
        "email",
      ]),
    ).toEqual(["Each source column can only be mapped once."]);
    const required = {
      ...schema,
      fields: schema.fields.map((field) => ({
        ...field,
        required: field.key === "email",
      })),
    };
    expect(mappingIssues(required, exact, suggestedMapping(exact), [])).toEqual(
      ["Map every required field."],
    );
    expect(
      mappingIssues(required, fuzzy, suggestedMapping(fuzzy), ["email"]),
    ).toEqual([]);
  });
});
