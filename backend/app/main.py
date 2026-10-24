from __future__ import annotations
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import load_settings
from app.services.app_service import HealthDocService, NotFound
from app.services.ingestion.validate import ValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def create_app(settings=None, service=None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="HealthDoc AI", version="1.0.0",
                  description="Educational document search and Q&A. Not medical, legal or insurance advice.")
    app.state.service = service or HealthDocService(settings, background=True)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(ValidationError)
    async def _v(_: Request, e: ValidationError):
        return JSONResponse({"error": {"code": e.code, "message": str(e)}}, status_code=e.status)

    @app.exception_handler(NotFound)
    async def _n(_: Request, e: NotFound):
        return JSONResponse({"error": {"code": "not_found", "message": str(e)}}, status_code=404)

    @app.exception_handler(Exception)
    async def _x(_: Request, e: Exception):
        logging.getLogger("healthdoc").error("unhandled %s", type(e).__name__)  # type only: never log document text
        return JSONResponse({"error": {"code": "internal_error", "message": "Something went wrong on the server."}}, status_code=500)

    app.include_router(router)
    return app


app = create_app()
