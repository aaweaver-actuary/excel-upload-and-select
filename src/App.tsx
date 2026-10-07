import { ChangeEvent, useMemo, useState } from 'react';
import * as XLSX from 'xlsx';

export type CanonicalField =
  | 'firstName'
  | 'lastName'
  | 'email'
  | 'phone'
  | 'company'
  | 'state';

export type FieldMapping = Record<CanonicalField, string | null>;

export type ExcelRow = Record<string, string | number | boolean | null>;

export const CANONICAL_FIELDS: Array<{ key: CanonicalField; label: string }> = [
  { key: 'firstName', label: 'First Name' },
  { key: 'lastName', label: 'Last Name' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'company', label: 'Company' },
  { key: 'state', label: 'State' },
];

export const COMMON_ALIASES: Record<CanonicalField, string[]> = {
  firstName: ['firstname', 'first name', 'given name', 'fname', 'first'],
  lastName: ['lastname', 'last name', 'surname', 'lname', 'family name', 'familyname'],
  email: ['email', 'e-mail', 'email address'],
  phone: ['phone', 'telephone', 'mobile', 'cell', 'phone number'],
  company: ['company', 'organization', 'org', 'employer', 'business'],
  state: ['state', 'province', 'region', 'location state'],
};

export function normalizeHeader(header: string): string {
  return header
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function detectColumnMapping(headers: string[]): FieldMapping {
  const normalized = headers.map((header) => ({ original: header, normalized: normalizeHeader(header) }));

  const mapping: FieldMapping = {
    firstName: null,
    lastName: null,
    email: null,
    phone: null,
    company: null,
    state: null,
  };

  for (const field of CANONICAL_FIELDS) {
    const aliases = COMMON_ALIASES[field.key];
    const match = normalized.find(({ normalized: name }) => {
      const exact = aliases.some((alias) => name === normalizeHeader(alias));
      const contains = aliases.some((alias) => name.includes(normalizeHeader(alias)));
      return exact || contains;
    });

    if (match) {
      mapping[field.key] = match.original;
    }
  }

  return mapping;
}

export function parseWorkbook(file: File): Promise<{ headers: string[]; previewRows: ExcelRow[]; worksheetName: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (event) => {
      try {
        const data = event.target?.result;
        if (!data) {
          reject(new Error('No file data was read.'));
          return;
        }

        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const json = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: '', raw: false });

        const headers = Object.keys(json[0] ?? {});
        const previewRows = json.slice(0, 10).map((row) => {
          const normalizedRow: ExcelRow = {};
          Object.entries(row).forEach(([key, value]) => {
            const normalizedValue = value === undefined ? null : typeof value === 'object' ? JSON.stringify(value) : value;
            normalizedRow[key] = normalizedValue as string | number | boolean | null;
          });
          return normalizedRow;
        });

        resolve({ headers, previewRows, worksheetName: firstSheetName });
      } catch (error) {
        reject(error);
      }
    };

    reader.onerror = () => reject(new Error('Unable to read the Excel file.'));
    reader.readAsArrayBuffer(file);
  });
}

export default function App() {
  const [fileName, setFileName] = useState<string>('');
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<ExcelRow[]>([]);
  const [mapping, setMapping] = useState<FieldMapping>({
    firstName: null,
    lastName: null,
    email: null,
    phone: null,
    company: null,
    state: null,
  });
  const [worksheetName, setWorksheetName] = useState<string>('');

  const preparedRows = useMemo(() => {
    if (!headers.length || !previewRows.length) {
      return [];
    }

    return previewRows.map((row) => {
      const prepared: Record<string, string | number | boolean | null> = {};
      for (const field of CANONICAL_FIELDS) {
        const selectedHeader = mapping[field.key];
        prepared[field.key] = selectedHeader ? row[selectedHeader] ?? null : null;
      }
      return prepared;
    });
  }, [headers, mapping, previewRows]);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) {
      return;
    }

    setFileName(selected.name);
    const parsed = await parseWorkbook(selected);
    setHeaders(parsed.headers);
    setPreviewRows(parsed.previewRows);
    setWorksheetName(parsed.worksheetName);
    setMapping(detectColumnMapping(parsed.headers));
  }

  function setFieldMapping(field: CanonicalField, header: string | null) {
    setMapping((current) => ({ ...current, [field]: header }));
  }

  return (
    <div className="app-shell">
      <div className="panel">
        <h1>Excel Upload and Select</h1>
        <label className="file-input-label">
          <span>Choose Excel file</span>
          <input type="file" accept=".xlsx,.xls,.csv" onChange={handleFileChange} />
        </label>

        {fileName ? (
          <div className="file-meta">
            <strong>{fileName}</strong>
            <span>Worksheet: {worksheetName}</span>
          </div>
        ) : null}

        {headers.length ? (
          <>
            <h2>Column mapping</h2>
            <div className="mapping-grid">
              {CANONICAL_FIELDS.map((field) => (
                <label key={field.key} className="mapping-field">
                  <span>{field.label}</span>
                  <select
                    value={mapping[field.key] ?? ''}
                    onChange={(event) => setFieldMapping(field.key, event.target.value || null)}
                  >
                    <option value="">Not mapped</option>
                    {headers.map((header) => (
                      <option key={header} value={header}>
                        {header}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>

            <div className="preview-section">
              <h2>Column preview</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {headers.map((header) => (
                        <th key={header}>{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, index) => (
                      <tr key={`${index}-${row[headers[0] ?? 'row']}`}>
                        {headers.map((header) => (
                          <td key={`${index}-${header}`}>{String(row[header] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="preview-section">
              <h2>Prepared data</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {CANONICAL_FIELDS.map((field) => (
                        <th key={field.key}>{field.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preparedRows.map((row, index) => (
                      <tr key={`prepared-${index}`}>
                        {CANONICAL_FIELDS.map((field) => (
                          <td key={`${field.key}-${index}`}>{String(row[field.key] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
