import ExcelJS from "exceljs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cellValue, parseSheet, readFile, readWorkbook } from "./excel";
import { workbook } from "./test/fixtures";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Excel parsing", () => {
  it("reads a real XLSX file and keeps every row and worksheet", async () => {
    const book = workbook();
    book.addWorksheet("Second").addRows([["Email"], ["x@example.com"]]);
    const bytes = await book.xlsx.writeBuffer();
    const parsed = await readWorkbook(
      new File([bytes], "CONTACTS.XLSX"),
      bytes.byteLength,
    );
    expect(parsed.worksheets.map((sheet) => sheet.name)).toEqual([
      "Contacts",
      "Second",
    ]);
    expect(parseSheet(parsed, parsed.worksheets[0].id, 12).rows).toHaveLength(
      12,
    );
    expect(parseSheet(parsed, parsed.worksheets[1].id, 12).rows).toEqual([
      { A: "x@example.com" },
    ]);
  });

  it("preserves physical positions for missing and duplicate headers", () => {
    const book = workbook(0, ["Email", null, "Email", 42]);
    book.worksheets[0].addRow(["one", false, "two", 0]);
    book.worksheets[0].addRow(["", null, "", null]);
    const parsed = parseSheet(book, 1, 2);
    expect(parsed.columns).toEqual([
      { id: "A", label: "Email" },
      { id: "B", label: "" },
      { id: "C", label: "Email" },
      { id: "D", label: "42" },
    ]);
    expect(parsed.rows).toEqual([
      { A: "one", B: false, C: "two", D: 0 },
      { A: "", B: null, C: "", D: null },
    ]);
  });

  it("preserves interior empty rows and ignores trailing formatting", () => {
    const book = workbook(0);
    const sheet = book.worksheets[0];
    sheet.addRow(["One"]);
    sheet.getRow(4).getCell(1).value = "Two";
    sheet.getRow(6).getCell(1).font = { bold: true };
    expect(parseSheet(book, 1, 3).rows).toEqual([
      { A: "One", B: null },
      { A: null, B: null },
      { A: "Two", B: null },
    ]);
  });

  it.each([
    [null, null],
    [undefined, null],
    ["text", "text"],
    [true, true],
    [false, false],
    [0, 0],
    [1.25, 1.25],
    [new Date("2025-01-01T00:00:00Z"), "2025-01-01T00:00:00.000Z"],
    [{ richText: [{ text: "Hello " }, { text: "world" }] }, "Hello world"],
    [{ text: "Example", hyperlink: "https://example.com" }, "Example"],
    [{ formula: "1+1", result: 2 }, 2],
    [{ sharedFormula: "A1", result: false }, false],
  ])("converts Excel cells into JSON-safe scalars", (value, expected) => {
    expect(cellValue(value as ExcelJS.CellValue, "A2")).toEqual(expected);
  });

  it.each([Number.POSITIVE_INFINITY, {}])(
    "rejects unsupported cells with their location",
    (value) => {
      expect(() => cellValue(value as ExcelJS.CellValue, "B3")).toThrow(
        "Cell B3",
      );
    },
  );

  it("previews uncached formulas and errors for backend row diagnostics", () => {
    expect(cellValue({ formula: "1+1" }, "C4")).toBe("1+1");
    expect(cellValue({ sharedFormula: "C4" }, "C5")).toBe("C4");
    expect(cellValue({ error: "#N/A" }, "C6")).toBe("#N/A");
  });

  it("rejects unsupported formats, oversized files, and corrupt workbooks", async () => {
    await expect(readWorkbook(new File(["x"], "book.xls"), 10)).rejects.toThrow(
      ".xlsx",
    );
    await expect(
      readWorkbook(new File(["123"], "book.xlsx"), 2),
    ).rejects.toThrow("file size limit");
    await expect(
      readWorkbook(new File(["corrupt"], "book.xlsx"), 100),
    ).rejects.toThrow("Unable to open");
  });

  it("rejects a workbook without worksheets", async () => {
    const bytes = await new ExcelJS.Workbook().xlsx.writeBuffer();
    await expect(
      readWorkbook(new File([bytes], "empty.xlsx"), 10000),
    ).rejects.toThrow("any worksheets");
  });

  it("rejects missing sheets, missing headers, empty data, and oversized worksheets", () => {
    expect(() => parseSheet(workbook(), 42, 100)).toThrow("does not exist");
    const blank = new ExcelJS.Workbook();
    blank.addWorksheet("Blank");
    expect(() => parseSheet(blank, 1, 100)).toThrow("no headers");
    expect(() => parseSheet(workbook(0), 1, 100)).toThrow("no data rows");
    expect(() => parseSheet(workbook(2), 1, 1)).toThrow("limited to 1 rows");
  });

  it.each(["invalid", "failure"])("reports FileReader errors", async (mode) => {
    class Reader {
      result = "not an ArrayBuffer";
      onload!: () => void;
      onerror!: () => void;
      readAsArrayBuffer() {
        if (mode === "invalid") this.onload();
        else this.onerror();
      }
    }
    vi.stubGlobal("FileReader", Reader);
    await expect(readFile(new File([], "x.xlsx"))).rejects.toThrow(
      mode === "invalid" ? "No file data" : "Unable to read",
    );
  });

  it("gives a useful workbook error for a non-Error failure", async () => {
    class Reader {
      readAsArrayBuffer() {
        // eslint-disable-next-line @typescript-eslint/only-throw-error -- Exercise failures from third-party code that throws non-Error values.
        throw "unexpected";
      }
    }
    vi.stubGlobal("FileReader", Reader);
    await expect(readWorkbook(new File([], "x.xlsx"), 10)).rejects.toThrow(
      "invalid Excel data",
    );
  });
});
