"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .Routes.profiles import router as profiles_router
from .Routes.workbooks import router as workbooks_router
from .Routes.api_keys import router as api_keys_router
from .Routes.callers import router as callers_router
from .Routes.tools import router as tools_router
from .Routes.sources import router as sources_router
from .Routes.chat import router as chat_router
from .Routes.outputs import router as outputs_router


app = FastAPI(title="PAWM API", version="0.1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(profiles_router, prefix="/api")
app.include_router(workbooks_router, prefix="/api")
app.include_router(api_keys_router, prefix="/api")
app.include_router(callers_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(outputs_router, prefix="/api")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# -------------------------------------------------------------------
# Frontend
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "FRONTEND"


app.mount(
    "/assets",
    StaticFiles(directory=DIST_DIR / "assets"),
    name="assets",
)


@app.get("/{path:path}")
async def frontend(path: str):
    requested_file = DIST_DIR / path

    if requested_file.is_file():
        return FileResponse(requested_file)

    return FileResponse(DIST_DIR / "index.html")