import { ChangeEvent, useEffect, useState } from 'react';
import type ExcelJS from 'exceljs';
import { getSchema, matchColumns, processImport } from './api';
import { parseSheet, readWorkbook } from './excel';
import { mappingIssues, needsApproval, suggestedMapping } from './mapping';
import { useLatestTask } from './useLatestTask';
import type { DataRow, Mapping, ParsedSheet, ProcessResult, Schema, SourceColumn, Suggestion } from './types';

interface Upload { name: string; workbook: ExcelJS.Workbook }

function Table({ columns, rows }: { columns: SourceColumn[]; rows: DataRow[] }) {
  return <div className="table-wrap"><table>
    <thead><tr>{columns.map((column) => <th key={column.id}>{column.label || `Unnamed column ${column.id}`}</th>)}</tr></thead>
    <tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column.id}>{String(row[column.id] ?? '')}</td>)}</tr>)}</tbody>
  </table></div>;
}

export function ImportScreen({ schema }: { schema: Schema }) {
  const [upload, setUpload] = useState<Upload | null>(null);
  const [sheetId, setSheetId] = useState(0);
  const [parsed, setParsed] = useState<ParsedSheet | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [mapping, setMapping] = useState<Mapping>({});
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [result, setResult] = useState<ProcessResult | null>(null);
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

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    setUpload(null);
    resetSheet();
    void run(async (commit) => {
      const workbook = await readWorkbook(file, schema.settings.max_file_bytes);
      const source = { name: file.name, workbook };
      const id = workbook.worksheets[0].id;
      commit(() => { setUpload(source); setSheetId(id); });
      await prepare(source, id, commit);
    });
    event.currentTarget.value = '';
  }

  function selectSheet(source: Upload, id: number) {
    setSheetId(id);
    resetSheet();
    void run((commit) => prepare(source, id, commit));
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

  const issues = suggestions === null ? [] : mappingIssues(schema, suggestions, mapping, confirmed);
  const destinationColumns = schema.fields.map((field) => ({ id: field.key, label: field.label }));

  return <>
    <p>Import an .xlsx workbook, review its columns, then process the complete worksheet.</p>
    <p className="hint">Row 1 contains headers. Up to {schema.settings.max_rows.toLocaleString()} data rows and {schema.settings.max_file_bytes / 1024 / 1024} MiB per workbook.</p>
    <label className="file-input-label"><span>Choose Excel file</span>
      <input type="file" accept=".xlsx" onChange={handleFileChange} />
    </label>
    {upload !== null && <div className="file-meta">
      <strong>{upload.name}</strong>
      <label>Worksheet <select value={sheetId} onChange={(event) => selectSheet(upload, Number(event.target.value))}>
        {upload.workbook.worksheets.map((sheet) => <option key={sheet.id} value={sheet.id}>{sheet.name}</option>)}
      </select></label>
    </div>}
    {busy && <p role="status">Working…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {error && parsed !== null && suggestions === null &&
      <button onClick={() => selectSheet(upload!, sheetId)} disabled={busy}>Retry column matching</button>}
    {parsed !== null && <section className="preview-section">
      <h2>Column preview</h2><p>{parsed.rows.length.toLocaleString()} rows imported. Showing the first {schema.settings.preview_rows}.</p>
      <Table columns={parsed.columns} rows={parsed.rows.slice(0, schema.settings.preview_rows)} />
    </section>}
    {suggestions !== null && <>
      <h2>Column mapping</h2>
      <p className="hint">Exact matches are accepted automatically. Approve fuzzy suggestions, choose another column, or skip an optional field.</p>
      <div className="mapping-grid">{schema.fields.map((field) => {
        const suggestion = suggestions.find((item) => item.fieldKey === field.key)!;
        const pending = needsApproval(suggestion, mapping[field.key], confirmed);
        return <div key={field.key} className="mapping-field">
          <label><span>{field.label}{field.required ? ' (required)' : ''}</span>
            <select value={mapping[field.key] ?? ''} onChange={(event) => selectMapping(field.key, event.target.value)} disabled={busy}>
              <option value="">Not mapped / skip</option>
              {parsed!.columns.map((column) => <option key={column.id} value={column.id}>{column.label || 'Unnamed'} ({column.id})</option>)}
            </select>
          </label>
          <span className="hint">{suggestion.matchType}{suggestion.score !== null && ` · ${suggestion.score.toFixed(1)}% similarity`}</span>
          {suggestion.matchType === 'ambiguous' && <span className="hint">Choose a column explicitly or skip this field.</span>}
          {pending && (mapping[field.key] === null
            ? <button disabled={busy} onClick={() => selectMapping(field.key, '')}>Skip {field.label} mapping</button>
            : <button disabled={busy} onClick={() => approve(field.key)}>Approve {field.label} mapping</button>)}
        </div>;
      })}</div>
      {issues.length > 0 && <ul className="hint">{issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>}
      <button className="primary" disabled={busy || issues.length > 0} onClick={() => {
        setResult(null);
        void run(async (commit) => {
          const response = await processImport({ ...parsed!, mapping, confirmedFields: confirmed }, schema.settings.max_request_bytes);
          commit(() => setResult(response));
        });
      }}>Process data</button>
    </>}
    {result !== null && <section className="preview-section">
      <h2>Processing complete</h2>
      <p role="status">Processed {result.rowsProcessed.toLocaleString()} of {result.rowsReceived.toLocaleString()} imported rows.</p>
      <p>{result.mappedFields.length} fields mapped; {result.unmappedFields.length} fields unmapped.</p>
      <ul>{schema.fields.map((field) => <li key={field.key}>{field.label}: {result.nonEmptyCounts[field.key].toLocaleString()} nonempty values</li>)}</ul>
      <h3>Processed data preview</h3><Table columns={destinationColumns} rows={result.previewRows} />
    </section>}
  </>;
}

export default function App() {
  const [schema, setSchema] = useState<Schema | null>(null);
  const { busy, error, run } = useLatestTask();
  function loadSchema() {
    void run(async (commit) => {
      const response = await getSchema();
      commit(() => setSchema(response));
    });
  }
  useEffect(loadSchema, []);
  return <div className="app-shell"><main className="panel">
    <h1>Excel Upload and Select</h1>
    {busy && <p role="status">Loading column definitions…</p>}
    {error && <><p role="alert" className="error">{error}</p><button onClick={loadSchema}>Retry connection</button></>}
    {schema !== null && <ImportScreen schema={schema} />}
  </main></div>;
}
