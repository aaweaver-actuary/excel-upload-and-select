import { useImport } from "../../hooks/useImport";
import type { Schema } from "../../types";
import { JobProgress } from "../jobs/JobProgress";
import { ImportInstructions } from "./ImportInstructions";
import { FilePicker } from "./FilePicker";
import { WorksheetPicker } from "./WorksheetPicker";
import { ImportFeedback } from "./ImportFeedback";
import { ColumnPreview } from "./ColumnPreview";
import { MappingSection } from "./MappingSection";

export function ImportScreen({ schema }: { schema: Schema }) {
  const state = useImport(schema);

  return (
    <>
      <ImportInstructions settings={schema.settings} />
      <FilePicker onSelect={state.selectFile} />
      {state.upload !== null && (
        <WorksheetPicker
          filename={state.upload.name}
          worksheets={state.upload.worksheets}
          selectedId={state.sheetId}
          onSelect={state.selectSheet}
        />
      )}
      <ImportFeedback
        busy={state.busy}
        error={state.error}
        canRetryMatching={state.parsed !== null && state.suggestions === null}
        onRetryMatching={state.retryMatching}
      />
      {state.parsed !== null && (
        <ColumnPreview
          parsed={state.parsed}
          previewRows={schema.settings.preview_rows}
        />
      )}
      {state.suggestions !== null && (
        <MappingSection
          fields={schema.fields}
          suggestions={state.suggestions}
          columns={state.parsed!.columns}
          mapping={state.mapping}
          confirmed={state.confirmed}
          issues={state.issues}
          busy={state.busy}
          onSelect={state.selectMapping}
          onApprove={state.approve}
          onProcess={state.processData}
        />
      )}
      {state.result !== null && (
        <JobProgress key={state.result.job_id} initial={state.result} />
      )}
    </>
  );
}
