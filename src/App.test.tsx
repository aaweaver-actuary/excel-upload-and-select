import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MockInstance } from 'vitest';
import type ExcelJS from 'exceljs';
import App, { ImportScreen } from './App';
import * as excel from './excel';
import { completedJob, deferred, exact, fuzzy, response, schema, suggestions, workbook } from './test/fixtures';
import type { Schema, Suggestion } from './types';

let fetch: ReturnType<typeof vi.fn>;
let read: MockInstance<typeof excel.readWorkbook>;
beforeEach(() => {
  fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  read = vi.spyOn(excel, 'readWorkbook').mockResolvedValue(workbook());
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function choose(name = 'contacts.xlsx') {
  fireEvent.change(screen.getByLabelText('Choose Excel file'), { target: { files: [new File(['data'], name)] } });
}

async function start(matches: Suggestion[] = exact, book: ExcelJS.Workbook = workbook(), config: Schema = schema) {
  read.mockResolvedValue(book);
  fetch.mockResolvedValueOnce(response(config)).mockResolvedValueOnce(response({ suggestions: matches })).mockImplementation(() => Promise.resolve(response(completedJob)));
  render(<App />);
  await screen.findByLabelText('Choose Excel file');
  choose();
  await screen.findByRole('heading', { name: 'Column mapping' });
}

describe('import interface', () => {
  it('loads column definitions and retries an unavailable backend', async () => {
    fetch.mockRejectedValueOnce(new Error('Backend offline')).mockResolvedValueOnce(response(schema));
    render(<App />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading column definitions');
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend offline');
    await userEvent.click(screen.getByRole('button', { name: 'Retry connection' }));
    expect(await screen.findByLabelText('Choose Excel file')).toHaveAttribute('accept', '.xlsx');
  });

  it('submits all rows with exact matches and renders the processing summary', async () => {
    await start();
    expect(screen.getByLabelText('Worksheet')).toHaveValue('1');
    expect(screen.getByText(/12 rows imported/)).toBeInTheDocument();
    expect(screen.queryByText(' Person 11 ')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Approve/ })).not.toBeInTheDocument();
    const pending = deferred<Response>();
    fetch.mockImplementationOnce(() => pending.promise);
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    expect(screen.getByRole('button', { name: 'Process data' })).toBeDisabled();
    expect(screen.getByLabelText('First Name')).toBeDisabled();
    const form = fetch.mock.calls[2][1].body as FormData;
    const payload = JSON.parse(form.get('metadata') as string);
    expect(fetch.mock.calls[2][0]).toBe('/api/v1/jobs');
    expect((form.get('file') as File).name).toBe('contacts.xlsx');
    expect(payload.sheet_name).toBe('Contacts');
    expect(payload.confirmedFields).toEqual([]);
    await act(async () => pending.resolve(response(completedJob)));
    expect(await screen.findByRole('heading', { name: 'Batch processing' })).toBeInTheDocument();
    expect(screen.getByText('12 of 12 rows processed; 0 scored; 12 need review; 0 invalid.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Download result workbook' })).toHaveAttribute('href', '/api/v1/jobs/job-1/result');
    await userEvent.selectOptions(screen.getByLabelText('First Name'), 'B');
    expect(screen.queryByText('Batch processing')).not.toBeInTheDocument();
  });

  it('requires fuzzy approval and sends the approved field explicitly', async () => {
    await start(fuzzy);
    expect(screen.getByText('fuzzy · 80.0% similarity')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Process data' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Approve Email mapping' }));
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    expect(await screen.findByText('Batch processing')).toBeInTheDocument();
    expect(JSON.parse(fetch.mock.calls[2][1].body.get('metadata')).confirmedFields).toEqual(['email']);
  });

  it('lets a user skip fuzzy suggestions and retry processing failures', async () => {
    await start(fuzzy);
    await userEvent.selectOptions(screen.getByLabelText('Email'), '');
    expect(screen.queryByRole('button', { name: 'Approve Email mapping' })).not.toBeInTheDocument();
    fetch.mockResolvedValueOnce(response({ detail: 'Processing failed' }, 422));
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Processing failed');
    await userEvent.selectOptions(screen.getByLabelText('Email'), 'B');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    expect(await screen.findByText('Batch processing')).toBeInTheDocument();
  });

  it('handles ambiguous, required, unmapped, and conflicting fields', async () => {
    const matches = suggestions([{ fieldKey: 'email', matchType: 'ambiguous', score: 100, candidates: [{ columnId: 'A', score: 100 }, { columnId: 'B', score: 100 }] }]);
    const config = { ...schema, fields: schema.fields.map((field) => ({ ...field, required: field.key === 'firstName' })) };
    await start(matches, workbook(1, [null, 'Email']), config);
    expect(screen.getByText('Unnamed column A')).toBeInTheDocument();
    expect(screen.getAllByRole('option', { name: 'Unnamed (A)' })).toHaveLength(6);
    expect(screen.getByText('Map at least one field.')).toBeInTheDocument();
    expect(screen.getByText('Map every required field.')).toBeInTheDocument();
    expect(screen.getByText('Choose a column explicitly or skip this field.')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('First Name (required)'), 'A');
    await userEvent.selectOptions(screen.getByLabelText('Email'), 'A');
    expect(screen.getByText('Each source column can only be mapped once.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Process data' })).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText('Email'), 'B');
    expect(screen.getByRole('button', { name: 'Process data' })).toBeEnabled();
  });

  it('renders a blank submitted cell in the preview', async () => {
    const book = workbook(0);
    book.worksheets[0].addRow(['Name', null]);
    await start(exact, book);
    expect(screen.getByRole('cell', { name: 'Name' })).toBeInTheDocument();
    expect(screen.getAllByRole('cell')[1]).toBeEmptyDOMElement();
  });

  it('retries failed matching without re-uploading the workbook', async () => {
    fetch.mockResolvedValueOnce(response(schema)).mockRejectedValueOnce(new Error('Matching offline')).mockResolvedValueOnce(response({ suggestions: exact }));
    render(<App />);
    await screen.findByLabelText('Choose Excel file');
    choose();
    expect(await screen.findByRole('alert')).toHaveTextContent('Matching offline');
    await userEvent.click(screen.getByRole('button', { name: 'Retry column matching' }));
    expect(await screen.findByRole('heading', { name: 'Column mapping' })).toBeInTheDocument();
    expect(read).toHaveBeenCalledTimes(1);
  });

  it('requires explicit skipping of ambiguous optional fields', async () => {
    const matches = suggestions([
      { fieldKey: 'firstName', matchType: 'exact', columnId: 'A', score: 100 },
      { fieldKey: 'email', matchType: 'ambiguous', score: 100 },
    ]);
    await start(matches);
    expect(screen.getByRole('button', { name: 'Process data' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Skip Email mapping' }));
    expect(screen.getByRole('button', { name: 'Process data' })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    await screen.findByText('Batch processing');
    expect(JSON.parse(fetch.mock.calls[2][1].body.get('metadata')).confirmedFields).toEqual(['email']);
  });

  it('reports unreadable files and ignores canceled selections', async () => {
    render(<ImportScreen schema={schema} />);
    const input = screen.getByLabelText('Choose Excel file');
    fireEvent.change(input, { target: { files: null } });
    fireEvent.change(input, { target: { files: [] } });
    expect(read).not.toHaveBeenCalled();
    read.mockRejectedValueOnce(new Error('Corrupt workbook'));
    choose();
    expect(await screen.findByRole('alert')).toHaveTextContent('Corrupt workbook');
    expect(screen.queryByRole('button', { name: 'Retry column matching' })).not.toBeInTheDocument();
  });

  it('allows recovery by selecting another worksheet when the first has no data', async () => {
    const book = workbook(0);
    book.addWorksheet('Data').addRows([['First Name'], ['Ada']]);
    read.mockResolvedValue(book);
    fetch.mockResolvedValue(response({ suggestions: exact }));
    render(<ImportScreen schema={schema} />);
    choose();
    expect(await screen.findByRole('alert')).toHaveTextContent('no data rows');
    await userEvent.selectOptions(screen.getByLabelText('Worksheet'), '2');
    expect(await screen.findByRole('heading', { name: 'Column mapping' })).toBeInTheDocument();
    expect(screen.getByText('Ada')).toBeInTheDocument();
  });

  it('resets mappings and results when switching worksheets', async () => {
    const book = workbook();
    book.addWorksheet('Second').addRows([['Email'], ['second@example.com']]);
    await start(exact, book);
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    await screen.findByText('Batch processing');
    fetch.mockResolvedValueOnce(response({ suggestions: suggestions([{ fieldKey: 'email', matchType: 'exact', columnId: 'A', score: 100 }]) }));
    await userEvent.selectOptions(screen.getByLabelText('Worksheet'), '2');
    await waitFor(() => expect(screen.getByLabelText('Email')).toHaveValue('A'));
    expect(screen.getByLabelText('First Name')).toHaveValue('');
    expect(screen.queryByText('Batch processing')).not.toBeInTheDocument();
  });

  it('ignores stale matching results after a newer file is selected', async () => {
    const old = deferred<Response>();
    fetch.mockResolvedValueOnce(response(schema)).mockImplementationOnce(() => old.promise).mockResolvedValueOnce(response({ suggestions: exact }));
    render(<App />);
    await screen.findByLabelText('Choose Excel file');
    choose('old.xlsx');
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    choose('new.xlsx');
    await screen.findByRole('heading', { name: 'Column mapping' });
    await act(async () => old.resolve(response({ suggestions: fuzzy })));
    expect(screen.getByText('new.xlsx')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve Email mapping' })).not.toBeInTheDocument();
  });

  it('ignores stale processing failures after switching worksheets', async () => {
    const book = workbook();
    book.addWorksheet('Second').addRows([['First Name'], ['New']]);
    await start(exact, book);
    const old = deferred<Response>();
    fetch.mockImplementationOnce(() => old.promise).mockResolvedValueOnce(response({ suggestions: exact }));
    await userEvent.click(screen.getByRole('button', { name: 'Process data' }));
    await userEvent.selectOptions(screen.getByLabelText('Worksheet'), '2');
    await screen.findByRole('heading', { name: 'Column mapping' });
    await act(async () => old.reject(new Error('Stale failure')));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('New')).toBeInTheDocument();
  });
});
