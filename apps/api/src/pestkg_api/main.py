from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .constants import API_VERSION
from .errors import register_exception_handlers
from .middleware import request_contract
from .models import ErrorEnvelope
from .neo4j_store import Neo4jStore
from .releases import ReleaseManager
from .routers import downloads, graph, health, registration_uses, releases, search, stats


def create_app(settings_override: Settings | None = None) -> FastAPI:
    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        manager = ReleaseManager(
            settings.data_dir,
            settings.state_dir,
            settings.release_id,
            cache_size=settings.repository_cache_size,
        )
        active_context = manager.resolve()
        application.state.settings = settings
        application.state.release_manager = manager
        application.state.neo4j = None
        application.state.neo4j_release_id = None
        if settings.neo4j_uri and settings.neo4j_password:
            application.state.neo4j = Neo4jStore(
                settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
            )
            application.state.neo4j_release_id = active_context.release_id
        yield
        if application.state.neo4j:
            application.state.neo4j.close()

    application = FastAPI(
        title="Multicountry Pesticide KG API",
        version=API_VERSION,
        lifespan=lifespan,
        responses={
            status_code: {
                "model": ErrorEnvelope,
                "description": description,
                "headers": {
                    "X-Request-ID": {
                        "description": "Request correlation identifier",
                        "schema": {"type": "string"},
                    }
                },
            }
            for status_code, description in {
                400: "Invalid request or release selector",
                404: "Entity, release, or resource not found",
                409: "Release lifecycle conflict",
                422: "Validation or configured result-limit failure",
                503: "No validated active release is ready",
            }.items()
        },
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-PestKG-Release", "X-Request-ID"],
        expose_headers=["X-PestKG-Release", "X-Request-ID"],
    )
    application.middleware("http")(request_contract)
    register_exception_handlers(application)

    application.include_router(health.router)
    application.include_router(releases.router)
    application.include_router(stats.router)
    application.include_router(search.router)
    application.include_router(registration_uses.router)
    application.include_router(graph.router)
    application.include_router(downloads.router)
    return application


app = create_app()
