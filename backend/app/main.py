from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse

from .columns import FIELDS, SETTINGS, Field, Settings
from .matching import match_columns
from .models import MatchRequest, ProcessRequest
from .processing import process_rows, validate_columns


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
                await JSONResponse({"detail": "The request exceeds the import size limit."}, status_code=413)(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay():
            return messages.pop(0)

        await self.app(scope, replay, send)


def create_app(fields: tuple[Field, ...] = FIELDS, settings: Settings = SETTINGS) -> FastAPI:
    app = FastAPI(title="Excel Import API", version="1.0.0")
    app.add_middleware(RequestSizeLimit, max_bytes=settings.max_request_bytes)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/schema")
    def schema():
        return {"fields": [asdict(field) for field in fields], "settings": asdict(settings)}

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
            return process_rows(request, fields, settings)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return app


app = create_app()
