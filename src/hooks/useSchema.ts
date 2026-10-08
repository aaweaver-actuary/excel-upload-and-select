import { useEffect, useState } from 'react';
import { getSchema } from '../api';
import type { Schema } from '../types';
import { useLatestTask } from './useLatestTask';

export function useSchema() {
  const [schema, setSchema] = useState<Schema | null>(null);
  const { busy, error, run } = useLatestTask();

  function loadSchema() {
    void run(async (commit) => {
      const response = await getSchema();
      commit(() => setSchema(response));
    });
  }

  useEffect(loadSchema, []);
  return { schema, busy, error, loadSchema };
}
