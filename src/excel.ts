import ExcelJS from "exceljs";
import type { CellValue, DataRow, ParsedSheet } from "./types";

export function readFile(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (!(reader.result instanceof ArrayBuffer)) {
        reject(new Error("No file data was read."));
        return;
      }
      resolve(reader.result);
    };
    reader.onerror = () => reject(new Error("Unable to read the Excel file."));
    reader.readAsArrayBuffer(file);
  });
}

export async function readWorkbook(
  file: File,
  maxBytes: number,
): Promise<ExcelJS.Workbook> {
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    throw new Error(
      "Choose an .xlsx Excel workbook. CSV and legacy .xls files are not supported.",
    );
  }
  if (file.size > maxBytes) {
    throw new Error(
      "The workbook exceeds the file size limit. Choose a smaller file.",
    );
  }
  const workbook = new ExcelJS.Workbook();
  try {
    await workbook.xlsx.load(await readFile(file));
  } catch (error) {
    throw new Error(
      `Unable to open this workbook: ${error instanceof Error ? error.message : "invalid Excel data"}`,
    );
  }
  if (!workbook.worksheets.length) {
    throw new Error("The spreadsheet does not contain any worksheets.");
  }
  return workbook;
}

export function cellValue(
  value: ExcelJS.CellValue,
  address: string,
): CellValue {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "object") {
    if ("richText" in value)
      return value.richText.map((part) => part.text).join("");
    if ("hyperlink" in value) return value.text;
    if ("formula" in value || "sharedFormula" in value) {
      if (value.result !== undefined) return cellValue(value.result, address);
      return String("formula" in value ? value.formula : value.sharedFormula);
    }
  }
  if (typeof value === "object" && "error" in value) return value.error;
  throw new Error(
    `Cell ${address} contains an unsupported value. Correct it before importing.`,
  );
}

export function parseSheet(
  workbook: ExcelJS.Workbook,
  sheetId: number,
  maxRows: number,
): ParsedSheet {
  const sheet = workbook.getWorksheet(sheetId);
  if (!sheet) throw new Error("The selected worksheet does not exist.");
  const columns = Array.from({ length: sheet.columnCount }, (_, index) => {
    const cell = sheet.getRow(1).getCell(index + 1);
    return {
      id: sheet.getColumn(index + 1).letter,
      label: String(cellValue(cell.value, cell.address) ?? "").trim(),
    };
  });
  if (!columns.some((column) => column.label.length > 0)) {
    throw new Error(
      "The selected worksheet has no headers in row 1. Choose another worksheet or add headers.",
    );
  }
  const rows: DataRow[] = [];
  let lastSourceRow = 1;
  sheet.eachRow((_row, number) => {
    lastSourceRow = number;
  });
  for (let rowNumber = 2; rowNumber <= lastSourceRow; rowNumber += 1) {
    const row = sheet.getRow(rowNumber);
    const data = Object.fromEntries(
      columns.map((column, index) => {
        const cell = row.getCell(index + 1);
        return [column.id, cellValue(cell.value, cell.address)];
      }),
    );
    rows.push(data);
    if (rows.length > maxRows)
      throw new Error(
        `Imports are limited to ${maxRows.toLocaleString()} rows. Choose a smaller worksheet.`,
      );
  }
  if (!rows.length) throw new Error("The selected worksheet has no data rows.");
  return { columns, rows };
}
