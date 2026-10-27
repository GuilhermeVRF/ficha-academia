"""FastAPI application: JSON API under /api plus the built PWA at /."""

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import auth
from app.config import settings
from app.routers import importing, workouts

app = FastAPI(title="Ficha de Academia")

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(workouts.router, dependencies=[Depends(auth.require_session)])
api.include_router(importing.router, dependencies=[Depends(auth.require_session)])
app.include_router(api)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Liveness probe for Railway."""
    return {"status": "ok"}


def _mount_frontend(static_dir: Path) -> None:
    """Serve the built SPA, falling back to index.html for client-side routes."""
    index_file = static_dir / "index.html"
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
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
