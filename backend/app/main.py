from dataclasses import asdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse

from .columns import FIELDS, SETTINGS, Field, Settings
from .matching import match_columns
from .models import MatchRequest, ProcessRequest
from .processing import process_rows, validate_columns
from .accounts import ACCOUNT_FIELDS
from .jobs_api import install_jobs
from .persistence import JobRepository, LocalArtifactStore


class RequestSizeLimit:
    """Bound streamed request bodies, including requests without Content-Length."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        messages = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message["body"])
            if size > self.max_bytes:
                body = {"error": {"code": "REQUEST_TOO_LARGE", "message": "The request exceeds the import size limit."}} if scope.get("path", "").startswith("/api/v1/") else {"detail": "The request exceeds the import size limit."}
                await JSONResponse(body, status_code=413)(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay():
            return messages.pop(0)

        await self.app(scope, replay, send)


def create_app(fields: tuple[Field, ...] = ACCOUNT_FIELDS, settings: Settings = SETTINGS) -> FastAPI:
    root = Path(settings.job_artifact_directory)
    repository, artifacts = JobRepository(root), LocalArtifactStore(root)

    @asynccontextmanager
    async def lifespan(app):
        repository.initialize()
        yield

    app = FastAPI(title="Excel Import API", version=settings.pipeline_version, lifespan=lifespan)
    app.state.repository, app.state.artifacts = repository, artifacts
    install_jobs(app, repository, artifacts, settings)
    app.add_middleware(RequestSizeLimit, max_bytes=settings.max_request_bytes)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/schema")
    def schema():
        public = ("suggestion_threshold", "candidate_limit", "max_rows", "max_file_bytes", "max_request_bytes", "preview_rows")
        return {"fields": [asdict(field) for field in fields], "settings": {key: getattr(settings, key) for key in public}}

    @app.post("/api/match-columns")
    def suggest(request: MatchRequest):
        try:
            validate_columns([column.id for column in request.columns])
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"suggestions": match_columns(request.columns, fields, settings)}

    @app.post("/api/process")
    def process(request: ProcessRequest):
        try:
            return process_rows(request, FIELDS if fields == ACCOUNT_FIELDS else fields, settings)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return app


app = create_app()
