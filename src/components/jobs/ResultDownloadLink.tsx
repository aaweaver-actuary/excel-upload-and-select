import { BaseLink } from "../base/BaseLink";

export function ResultDownloadLink({ jobId }: { jobId: string }) {
  return (
    <BaseLink href={`/api/v1/jobs/${encodeURIComponent(jobId)}/result`}>
      Download result workbook
    </BaseLink>
  );
}
