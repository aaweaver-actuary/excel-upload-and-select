import type { Schema } from "../../types";
import { BaseParagraph } from "../base/BaseParagraph";
import { HintParagraph } from "../shared/HintParagraph";

export function ImportInstructions({
  settings,
}: {
  settings: Schema["settings"];
}) {
  return (
    <>
      <BaseParagraph>
        Import an .xlsx workbook, review its columns, then process the complete
        worksheet.
      </BaseParagraph>
      <HintParagraph>
        Row 1 contains headers. Up to {settings.max_rows.toLocaleString()} data
        rows and {settings.max_file_bytes / 1024 / 1024} MiB per workbook.
      </HintParagraph>
    </>
  );
}
