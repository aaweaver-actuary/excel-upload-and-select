export type CellValue = string | number | boolean | null;
export type DataRow = Record<string, CellValue>;
export interface SourceColumn {
  id: string;
  label: string;
}
export interface FieldDefinition {
  key: string;
  label: string;
  aliases: string[];
  required: boolean;
}
export interface Schema {
  fields: FieldDefinition[];
  settings: {
    suggestion_threshold: number;
    candidate_limit: number;
    max_rows: number;
    max_file_bytes: number;
    max_request_bytes: number;
    preview_rows: number;
  };
}
export interface Suggestion {
  fieldKey: string;
  matchType: "exact" | "fuzzy" | "ambiguous" | "unmatched";
  columnId: string | null;
  score: number | null;
  candidates: Array<{ columnId: string; score: number }>;
}
export type Mapping = Record<string, string | null>;
export interface ParsedSheet {
  columns: SourceColumn[];
  rows: DataRow[];
}
export interface ProcessRequest extends ParsedSheet {
  mapping: Mapping;
  confirmedFields: string[];
}
export interface ProcessResult {
  rowsReceived: number;
  rowsProcessed: number;
  mappedFields: string[];
  unmappedFields: string[];
  nonEmptyCounts: Record<string, number>;
  previewRows: DataRow[];
}
export interface BatchJob {
  job_id: string;
  status:
    | "queued"
    | "running"
    | "completed"
    | "completed_with_issues"
    | "failed";
  stage?: string | null;
  total_rows?: number;
  processed_rows?: number;
  scored_rows?: number;
  needs_review_rows?: number;
  invalid_rows?: number;
  error_message?: string | null;
  versions?: {
    pipeline: string;
    provider: string;
    provider_version: string;
    naics_reference: string;
    reference_data: string;
    scorers: Record<string, string>;
  };
}

export type RowStatus =
  | "scored"
  | "scored_with_warnings"
  | "needs_review"
  | "invalid";
export interface CanonicalAccount {
  source_row_number: number;
  account_id: string | null;
  business_name: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  naics: string | null;
}
export interface RowResult {
  source_row_number: number;
  status: RowStatus;
  issues: string[];
  canonical_account: CanonicalAccount | null;
  naics: {
    input_value: CellValue;
    final_value: string | null;
    source: "submitted" | "third_party" | "none";
    status: string;
    provider: string | null;
    provider_record_id: string | null;
    provider_confidence: number | null;
    retrieved_at: string | null;
    warning_codes: string[];
  };
  scores: Record<
    string,
    { value: number | null; status: string; issues: string[] }
  >;
}
export interface JobRows {
  job_id: string;
  offset: number;
  limit: number;
  total: number;
  rows: RowResult[];
}
