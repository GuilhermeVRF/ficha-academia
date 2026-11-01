"""FastAPI application: JSON API under /api plus the built PWA at /."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import auth
from app.config import settings
from app.db import SessionLocal
from app.routers import importing, invites, sessions, workouts
from app.services.admin import ensure_admin


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Make the database's admin match ADMIN_* before serving requests."""
    if settings.admin_email:
        with SessionLocal() as session:
            ensure_admin(session, settings.admin_name, settings.admin_email, settings.admin_password)
            session.commit()
    yield


app = FastAPI(title="Pino", lifespan=lifespan)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
# Every handler also takes the user itself; the router-level check guards future endpoints.
api.include_router(invites.router)
api.include_router(workouts.router, dependencies=[Depends(auth.current_user)])
api.include_router(importing.router, dependencies=[Depends(auth.current_user)])
api.include_router(sessions.router, dependencies=[Depends(auth.current_user)])
app.include_router(api)


@app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
def healthz() -> dict[str, str]:
    """Liveness probe for Railway."""
    return {"status": "ok"}


def _mount_frontend(static_dir: Path) -> None:
    """Serve the built SPA, falling back to index.html for client-side routes."""
    index_file = static_dir / "index.html"
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Return a static file, or index.html so the client router can handle the path."""
        if path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static_dir.resolve()):
            return FileResponse(candidate, headers=_cache_headers(path))
        return FileResponse(index_file, headers={"Cache-Control": "no-cache"})


def _cache_headers(path: str) -> dict[str, str]:
    """Never cache the service worker so app updates are picked up promptly."""
    if path in {"sw.js", "manifest.webmanifest"} or path.startswith("workbox-"):
        return {"Cache-Control": "no-cache"}
    return {}


_static_dir = Path(settings.static_dir)
if (_static_dir / "index.html").is_file():
    _mount_frontend(_static_dir)
