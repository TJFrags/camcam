"""
CamCam FastAPI Application Factory
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from camcam.web.routes import router as api_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="CamCam - Nikon D3100 Quick Settings & Remote Shutter",
        description="FastAPI Web Interface for Wired USB Nikon D3100 DSLR Control",
        version="1.0.0",
    )

    # Enable CORS for local network and dev tools
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include REST API routes
    app.include_router(api_router)

    # Serve static assets
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "CamCam API is running. Static files not found."}

    return app


app = create_app()
