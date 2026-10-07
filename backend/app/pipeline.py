import logging
import time

from .accounts import validate_account
from .enrichment import NaicsReference, NaicsResolver, UnconfiguredProvider
from .job_models import ApplicationError, JobMetadata, RowResult
from .persistence import timestamp
from .scoring import FeatureBuilder, ReferenceDataService, score_accounts
from .workbooks import canonical_rows, input_naics, read_workbook, render_workbook, validate_mapping

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, repository, artifacts, settings, provider=None, naics_reference=None, scorers=(), reference=None):
        self.repository, self.artifacts, self.settings = repository, artifacts, settings
        self.provider = provider or UnconfiguredProvider()
        self.naics_reference = naics_reference or NaicsReference()
        self.scorers = tuple(scorers)
        self.reference = reference or ReferenceDataService()
        if len({scorer.name for scorer in scorers}) != len(scorers):
            raise ValueError("Scorer names must be unique.")

    def versions(self):
        return {"pipeline": self.settings.pipeline_version, "provider": self.provider.name,
                "provider_version": self.provider.version, "naics_reference": self.naics_reference.version,
                "reference_data": self.reference.version, "scorers": {scorer.name: scorer.version for scorer in self.scorers}}

    async def process(self, job):
        job_id = job["id"]
        timings, started, stage_started, current_stage = {}, time.monotonic(), time.monotonic(), "ingestion"

        def stage(name):
            nonlocal stage_started, current_stage
            now = time.monotonic()
            timings[current_stage] = now - stage_started
            stage_started, current_stage = now, name
            self.repository.update(job_id, stage=name)
            logger.info("stage_started", extra={"job_id": job_id, "stage": name})

        try:
            if job["attempts"] > 1 and job["versions"] != self.versions():
                raise ApplicationError("PIPELINE_VERSION_CHANGED", "Processing configuration changed during recovery. Resubmit the workbook.")
            self.repository.update(job_id, versions=self.versions(), error_code=None, error_message=None)
            metadata = JobMetadata.model_validate(job["metadata"])
            workbook = read_workbook(self.artifacts.open_input(job_id), job["original_filename"], metadata.sheet_name, self.settings)
            stage("validation")
            validate_mapping(workbook, metadata, self.settings)
            accounts = canonical_rows(workbook, metadata)
            issues = {account.source_row_number: validate_account(account) + workbook.cell_issues.get(account.source_row_number, []) for account in accounts}
            invalid = {number for number, codes in issues.items() if "MISSING_BUSINESS_NAME" in codes}
            stage("enrichment")
            resolver = NaicsResolver(self.provider, self.naics_reference, self.repository, self.settings)
            resolutions = await resolver.resolve(accounts, {number: input_naics(workbook, metadata, number) for number in workbook.rows}, job_id,
                lambda count: self.repository.update(job_id, processed_rows=count))
            stage("lookup")
            features = FeatureBuilder().build(accounts, resolutions, self.reference)
            stage("scoring")
            scores = score_accounts(features, self.scorers, invalid)
            results = []
            for account in accounts:
                number = account.source_row_number
                codes = issues[number] + resolutions[number].warning_codes
                for score in scores[number].values():
                    codes += score.issues
                if not self.scorers:
                    codes.append("SCORING_NOT_CONFIGURED")
                if number in invalid:
                    status = "invalid"
                elif not scores[number] or any(score.status != "scored" or score.value is None for score in scores[number].values()):
                    status = "needs_review"
                else:
                    status = "scored_with_warnings" if codes else "scored"
                results.append(RowResult(source_row_number=number, status=status, issues=list(dict.fromkeys(codes)),
                                         naics=resolutions[number], scores=scores[number]))
            self.repository.save_results(job_id, results)
            counts = {status: sum(row.status == status for row in results) for status in ("scored", "scored_with_warnings", "needs_review", "invalid")}
            stage("output")
            summary = {"Job ID": job_id, "Original filename": job["original_filename"], "Processed timestamp": timestamp(),
                       "Rows submitted": len(results), **{f"Rows {key}": value for key, value in counts.items()},
                       "NAICS supplied": sum(row.naics.input_value is not None for row in results),
                       "NAICS externally enriched": sum(row.naics.source == "third_party" for row in results),
                       "NAICS unresolved": sum(row.naics.final_value is None for row in results),
                       "Versions": self.versions(), "Column mapping": metadata.mapping}
            uri = self.artifacts.save_output(job_id, render_workbook(workbook, results, summary))
            timings["output"] = time.monotonic() - stage_started
            self.repository.update(job_id, status="completed_with_issues" if counts["needs_review"] or counts["invalid"] or counts["scored_with_warnings"] else "completed",
                output_artifact_uri=uri, finished_at=timestamp(), processed_rows=len(results),
                scored_rows=counts["scored"] + counts["scored_with_warnings"], needs_review_rows=counts["needs_review"], invalid_rows=counts["invalid"],
                metrics={"stage_seconds": timings, "duration_seconds": time.monotonic() - started, "naics": resolver.metrics, "row_counts": counts})
            logger.info("job_completed", extra={"job_id": job_id, "stage": "output"})
        except Exception as error:
            fatal = isinstance(error, ApplicationError) and error.status < 500
            exhausted = job["attempts"] >= self.settings.worker_max_attempts
            self.repository.update(job_id, status="failed" if fatal or exhausted else "queued",
                finished_at=timestamp() if fatal or exhausted else None,
                error_code=error.code if isinstance(error, ApplicationError) else "PROCESSING_ERROR",
                error_message=error.message if isinstance(error, ApplicationError) else "Processing could not complete.")
            # Do not include exception text/payloads: vendor errors can contain insured information.
            logger.error("job_failed", extra={"job_id": job_id, "stage": current_stage, "error_type": type(error).__name__})
