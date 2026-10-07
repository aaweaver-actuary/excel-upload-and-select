import type { ProcessRequest, ProcessResult, Schema, SourceColumn, Suggestion } from './types';

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

async function readResponse<T>(response: Response): Promise<T> {
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`The server returned an unreadable response (${response.status}).`);
  }
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : `The request failed (${response.status}). Check your import and try again.`);
  }
  return data as T;
}

export function getSchema(): Promise<Schema> {
  return fetch('/api/schema').then(readResponse<Schema>);
}

async function post<T>(path: string, payload: unknown, maxBytes: number): Promise<T> {
  const body = JSON.stringify(payload);
  if (new TextEncoder().encode(body).byteLength > maxBytes) {
    throw new Error('The imported data exceeds the request size limit. Choose a smaller worksheet.');
  }
  return readResponse<T>(await fetch(`/api/${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body,
  }));
}

export function matchColumns(columns: SourceColumn[], maxBytes: number): Promise<{ suggestions: Suggestion[] }> {
  return post('match-columns', { columns }, maxBytes);
}

export function processImport(payload: ProcessRequest, maxBytes: number): Promise<ProcessResult> {
  return post('process', payload, maxBytes);
}
