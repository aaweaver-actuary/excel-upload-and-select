import { afterEach, describe, expect, it, vi } from 'vitest';
import { errorMessage, getSchema, matchColumns, processImport } from './api';
import { response, result, schema } from './test/fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('API', () => {
  it('loads the schema and sends matching and complete processing payloads', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(schema)).mockResolvedValueOnce(response({ suggestions: [] })).mockResolvedValueOnce(response(result));
    vi.stubGlobal('fetch', fetch);
    expect(await getSchema()).toEqual(schema);
    expect(await matchColumns([{ id: 'A', label: 'Email' }], 1024)).toEqual({ suggestions: [] });
    const payload = { columns: [{ id: 'A', label: 'Email' }], rows: [{ A: false }, { A: 0 }], mapping: { email: 'A' }, confirmedFields: [] };
    expect(await processImport(payload, 1024)).toEqual(result);
    expect(fetch.mock.calls[0][0]).toBe('/api/schema');
    expect(fetch.mock.calls[1][0]).toBe('/api/match-columns');
    expect(fetch.mock.calls[2][0]).toBe('/api/process');
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual(payload);
  });

  it('counts UTF-8 bytes and allows exactly the configured request limit', async () => {
    const columns = [{ id: 'A', label: 'Émail' }];
    const bytes = new TextEncoder().encode(JSON.stringify({ columns })).byteLength;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ suggestions: [] })));
    await expect(matchColumns(columns, bytes)).resolves.toEqual({ suggestions: [] });
    await expect(matchColumns(columns, bytes - 1)).rejects.toThrow('request size limit');
  });

  it.each([
    [response({ detail: 'Confirm email' }, 422), 'Confirm email'],
    [response({ error: { code: 'INVALID_REQUEST', message: 'Invalid job mapping' } }, 422), 'Invalid job mapping'],
    [response({ detail: [{ msg: 'invalid' }] }, 422), 'request failed (422)'],
    [new Response('<html>too large</html>', { status: 413 }), 'unreadable response (413)'],
  ])('reports API and unreadable proxy errors', async (reply, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply));
    await expect(getSchema()).rejects.toThrow(message);
  });

  it('preserves network errors and gives a fallback for unknown exceptions', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Offline')));
    await expect(getSchema()).rejects.toThrow('Offline');
    expect(errorMessage(new Error('Offline'))).toBe('Offline');
    expect(errorMessage(null)).toContain('Please try again');
  });
});
