import json
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.responses import FileResponse, JSONResponse

from .job_models import ApplicationError, JobMetadata, RowStatus
from .pipeline import Pipeline
from .workbooks import read_workbook, validate_mapping


def install_jobs(app, repository, artifacts, settings):
    router = APIRouter(prefix="/api/v1/jobs")

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, error: ApplicationError):
        return JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Request, error: RequestValidationError):
        if request.url.path.startswith("/api/v1/"):
            return JSONResponse({"error": {"code": "INVALID_REQUEST", "message": "The request does not match the required contract."}}, status_code=422)
        # Preserve the legacy error response without echoing supplied workbook rows.
        return JSONResponse({"detail": "Invalid request."}, status_code=422)

    @router.post("", status_code=202)
    def create_job(file: UploadFile = File(), metadata: str = Form()):
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ApplicationError("INVALID_REQUEST", "Metadata contains duplicate object keys.")
                result[key] = value
            return result
        try:
            options = JobMetadata.model_validate(json.loads(metadata, object_pairs_hook=unique_object))
        except (ValidationError, ValueError) as error:
            raise ApplicationError("INVALID_REQUEST", "Metadata must contain sheet_name, mapping and optional confirmedFields.") from error
        # Both content length and actual bytes are bounded; filenames never become paths.
        data = file.file.read(settings.max_file_bytes + 1)
        filename = Path((file.filename or "workbook.xlsx").replace("\\", "/")).name[:255]
        workbook = read_workbook(data, filename, options.sheet_name, settings)
        validate_mapping(workbook, options, settings)
        job_id = str(uuid4())
        uri = artifacts.save_input(job_id, data)
        try:
            job = repository.create(job_id, filename, uri, options, len(workbook.rows), Pipeline(repository, artifacts, settings).versions())
        except sqlite3.Error as error:
            artifacts.remove(job_id)
            raise ApplicationError("JOB_PERSISTENCE_ERROR", "Unable to accept the job. Please retry.", 503) from error
        return {"job_id": job_id, "status": job["status"], "created_at": job["created_at"]}

    @router.get("/{job_id}")
    def get_job(job_id: UUID):
        job = repository.get(str(job_id))
        return {"job_id": job["id"], **{key: job[key] for key in (
            "status", "stage", "total_rows", "processed_rows", "scored_rows", "needs_review_rows", "invalid_rows",
            "created_at", "started_at", "finished_at", "error_code", "error_message", "versions", "metrics")}}

    @router.get("/{job_id}/rows")
    def get_rows(job_id: UUID, offset: int = Query(default=0, ge=0),
                 limit: int = Query(default=50, ge=1, le=200), status: RowStatus | None = None):
        job = repository.get(str(job_id))
        if job["status"] not in {"completed", "completed_with_issues"}:
            raise ApplicationError("JOB_NOT_READY", "The result is not available.", 409)
        total, rows = repository.results(str(job_id), offset, limit, status)
        return {"job_id": str(job_id), "offset": offset, "limit": limit, "total": total, "rows": rows}

    @router.get("/{job_id}/result")
    def get_result(job_id: UUID):
        job = repository.get(str(job_id))
        if job["status"] not in {"completed", "completed_with_issues"}:
            raise ApplicationError("JOB_NOT_READY", "The result is not available.", 409)
        path = artifacts.output_path(str(job_id))
        if not path.is_file():
            raise ApplicationError("ARTIFACT_STORAGE_ERROR", "The result artifact is unavailable.", 503)
        return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            filename=f"result-{job_id}.xlsx")

    @app.get("/api/ready")
    def ready():
        try:
            repository.root.mkdir(parents=True, exist_ok=True)
            probe = repository.root / f".ready-{uuid4()}"
            probe.write_bytes(b"")
            probe.unlink()
            healthy = repository.ready(settings.worker_stale_seconds)
        except (OSError, sqlite3.Error):
            healthy = False
        return JSONResponse({"status": "ready" if healthy else "unavailable"}, status_code=200 if healthy else 503)

    app.include_router(router)
