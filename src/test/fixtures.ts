import ExcelJS from 'exceljs';
import type { BatchJob, ProcessResult, Schema, Suggestion } from '../types';

export const schema: Schema = {
  fields: ['firstName', 'lastName', 'email', 'phone', 'company', 'state'].map((key, index) => ({
    key, label: ['First Name', 'Last Name', 'Email', 'Phone', 'Company', 'State'][index], aliases: [], required: false,
  })),
  settings: { suggestion_threshold: 80, candidate_limit: 3, max_rows: 50_000, max_file_bytes: 20 * 1024 * 1024, max_request_bytes: 64 * 1024 * 1024, preview_rows: 10 },
};

export function suggestions(overrides: Partial<Suggestion>[] = []): Suggestion[] {
  return schema.fields.map((field) => ({
    fieldKey: field.key, matchType: 'unmatched', columnId: null, score: null, candidates: [],
    ...overrides.find((item) => item.fieldKey === field.key),
  }));
}

export const exact = suggestions([{ fieldKey: 'firstName', matchType: 'exact', columnId: 'A', score: 100 }]);
export const fuzzy = suggestions([
  { fieldKey: 'firstName', matchType: 'exact', columnId: 'A', score: 100 },
  { fieldKey: 'email', matchType: 'fuzzy', columnId: 'B', score: 80, candidates: [{ columnId: 'B', score: 80 }] },
]);

export function workbook(count = 12, headers: ExcelJS.CellValue[] = ['First Name', 'Emial']): ExcelJS.Workbook {
  const book = new ExcelJS.Workbook();
  const sheet = book.addWorksheet('Contacts');
  sheet.addRow(headers);
  for (let index = 0; index < count; index++) sheet.addRow([` Person ${index} `, ` person${index}@example.com `]);
  return book;
}

export const result: ProcessResult = {
  rowsReceived: 12, rowsProcessed: 12, mappedFields: ['firstName'], unmappedFields: ['lastName', 'email', 'phone', 'company', 'state'],
  nonEmptyCounts: { firstName: 12, lastName: 0, email: 0, phone: 0, company: 0, state: 0 },
  previewRows: [{ firstName: 'Person 0', lastName: null, email: null, phone: null, company: null, state: null }],
};
export const completedJob: BatchJob = { job_id: 'job-1', status: 'completed_with_issues', total_rows: 12,
  processed_rows: 12, scored_rows: 0, needs_review_rows: 12, invalid_rows: 0 };

export function response(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
}

export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
