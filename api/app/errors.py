"""Format d'erreur unique : {code, message, details, path, timestamp}."""
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import DatabaseUnavailable

log = logging.getLogger("api.structures")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status, self.code, self.message = status, code, message
        self.details = details or []


def _body(request: Request, code: str, message: str, details=None) -> dict:
    return {
        "code": code,
        "message": message,
        "details": details or [],
        "path": request.url.path,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_body(request, exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p not in ("query", "path")), "issue": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=400, content=_body(request, "VALIDATION_ERROR", "Paramètres de requête invalides", details)
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        codes = {404: "RESOURCE_NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(request, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)),
        )

    @app.exception_handler(DatabaseUnavailable)
    async def db_down(request: Request, exc: DatabaseUnavailable):
        log.error("Base de données indisponible : %s", exc)
        return JSONResponse(
            status_code=503,
            content=_body(request, "DATABASE_UNAVAILABLE", "La base de données est momentanément indisponible"),
            headers={"Retry-After": "30"},
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("Erreur inattendue")
        return JSONResponse(status_code=500, content=_body(request, "INTERNAL_ERROR", "Erreur interne du serveur"))
