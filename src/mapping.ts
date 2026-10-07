import type { Mapping, Schema, Suggestion } from './types';

export function suggestedMapping(suggestions: Suggestion[]): Mapping {
  return Object.fromEntries(suggestions.map((suggestion) => [suggestion.fieldKey, suggestion.columnId]));
}

export function needsApproval(suggestion: Suggestion, selected: string | null, confirmed: string[]): boolean {
  return !confirmed.includes(suggestion.fieldKey) && (suggestion.matchType === 'ambiguous' ||
    (selected !== null && !(suggestion.matchType === 'exact' && suggestion.columnId === selected)));
}

export function mappingIssues(schema: Schema, suggestions: Suggestion[], mapping: Mapping, confirmed: string[]): string[] {
  const issues = [];
  const selected = Object.values(mapping).filter((value) => value !== null);
  if (!selected.length) issues.push('Map at least one field.');
  if (new Set(selected).size !== selected.length) issues.push('Each source column can only be mapped once.');
  if (schema.fields.some((field) => field.required && !mapping[field.key])) issues.push('Map every required field.');
  if (suggestions.some((suggestion) => needsApproval(suggestion, mapping[suggestion.fieldKey], confirmed))) {
    issues.push('Approve or change the suggested mappings before processing.');
  }
  return issues;
}
