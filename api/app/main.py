"""API REST de consultation des structures sanitaires (backend de WSO2 API Manager)."""
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import db, errors
from .routers import v1, v2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("api.structures")

app = FastAPI(
    title="API Structures sanitaires",
    version="2.0.0",
    description="Backend du Groupe 3 SI. Les clients passent par la passerelle WSO2, "
                "jamais directement par ce service.",
)
errors.install(app)
app.include_router(v1)
app.include_router(v2)


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Journal d'accès avec identifiant de corrélation (repris de WSO2 s'il est fourni)."""
    cid = request.headers.get("activityid") or request.headers.get("x-correlation-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    log.info("cid=%s %s %s -> %s (%.1f ms)", cid, request.method, request.url.path,
             response.status_code, (time.perf_counter() - start) * 1000)
    return response


@app.get("/health", tags=["supervision"], summary="État du backend et de la base")
def health():
    up = db.ping()
    return JSONResponse(
        status_code=200 if up else 503,
        content={"status": "UP" if up else "DEGRADED", "database": "UP" if up else "DOWN"},
    )
