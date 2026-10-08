import { useState } from 'react';
import type ExcelJS from 'exceljs';
import { createJob, matchColumns } from '../api';
import { parseSheet, readWorkbook } from '../excel';
import { mappingIssues, suggestedMapping } from '../mapping';
import type { BatchJob, Mapping, ParsedSheet, Schema, Suggestion } from '../types';
import { useLatestTask } from './useLatestTask';

interface Upload {
  name: string;
  file: File;
  workbook: ExcelJS.Workbook;
}

export function useImport(schema: Schema) {
  const [upload, setUpload] = useState<Upload | null>(null);
  const [sheetId, setSheetId] = useState(0);
  const [parsed, setParsed] = useState<ParsedSheet | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [mapping, setMapping] = useState<Mapping>({});
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [result, setResult] = useState<BatchJob | null>(null);
  const { busy, error, run, clearError } = useLatestTask();

  function resetSheet() {
    setParsed(null);
    setSuggestions(null);
    setMapping({});
    setConfirmed([]);
    setResult(null);
  }

  async function prepare(source: Upload, id: number, commit: (action: () => void) => void) {
    const data = parseSheet(source.workbook, id, schema.settings.max_rows);
    commit(() => setParsed(data));
    const response = await matchColumns(data.columns, schema.settings.max_request_bytes);
    commit(() => {
      setSuggestions(response.suggestions);
      setMapping(suggestedMapping(response.suggestions));
    });
  }

  function selectFile(file: File) {
    setUpload(null);
    resetSheet();
    void run(async (commit) => {
      const workbook = await readWorkbook(file, schema.settings.max_file_bytes);
      const source = { name: file.name, file, workbook };
      const id = workbook.worksheets[0].id;
      commit(() => { setUpload(source); setSheetId(id); });
      await prepare(source, id, commit);
    });
  }

  function selectSheet(id: number) {
    setSheetId(id);
    resetSheet();
    void run((commit) => prepare(upload!, id, commit));
  }

  function selectMapping(fieldKey: string, columnId: string) {
    setMapping((current) => ({ ...current, [fieldKey]: columnId || null }));
    setConfirmed((current) => [...current, fieldKey]);
    setResult(null);
    clearError();
  }

  function approve(fieldKey: string) {
    setConfirmed((current) => [...current, fieldKey]);
  }

  function retryMatching() {
    selectSheet(sheetId);
  }

  function processData() {
    setResult(null);
    void run(async (commit) => {
      const response = await createJob(upload!.file, upload!.workbook.getWorksheet(sheetId)!.name, mapping, confirmed);
      commit(() => setResult(response));
    });
  }

  const issues = suggestions === null ? [] : mappingIssues(schema, suggestions, mapping, confirmed);
  const selectedUpload = upload === null ? null : {
    name: upload.name,
    worksheets: upload.workbook.worksheets.map(sheet => ({ id: sheet.id, name: sheet.name })),
  };

  return {
    upload: selectedUpload, sheetId, parsed, suggestions, mapping, confirmed, result,
    busy, error, issues, selectFile, selectSheet, selectMapping, approve, retryMatching, processData,
  };
}
