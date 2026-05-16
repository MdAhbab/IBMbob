"""
AI CLI Orchestrator - Downloader Page Backend
Serves the React frontend and provides download API endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Get the directory paths
BACKEND_DIR = Path(__file__).parent
DOWNLOADER_DIR = BACKEND_DIR.parent
DIST_DIR = DOWNLOADER_DIR / "dist"
DOWNLOADS_DIR = DOWNLOADER_DIR / "downloads"

# Create FastAPI application
app = FastAPI(
    title="AI CLI Orchestrator - Downloader API",
    description="Backend API for AI CLI Orchestrator Downloader Page",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for downloads
if DOWNLOADS_DIR.exists():
    app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")

# Mount the React frontend (after building with npm run build)
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")


@app.get("/")
async def serve_frontend():
    """Serve the React frontend"""
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "name": "AI CLI Orchestrator - Downloader API",
        "version": "1.0.0",
        "status": "running",
        "message": "Frontend not built. Run 'npm run build' in downloader_page directory."
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-cli-orchestrator"
    }


@app.get("/api/version")
async def get_version():
    """Get application version and download links"""
    
    # Check which installers are available
    downloads = {}
    checksums = {}
    
    if DOWNLOADS_DIR.exists():
        # Check for Windows installer
        windows_exe = DOWNLOADS_DIR / "AI-CLI-Orchestrator-Setup.exe"
        if windows_exe.exists():
            downloads["windows"] = {
                "url": "/downloads/AI-CLI-Orchestrator-Setup.exe",
                "size": os.path.getsize(windows_exe),
                "available": True
            }
            checksums["windows"] = "sha256:pending"
        else:
            downloads["windows"] = {"available": False}
        
        # Check for macOS installer
        macos_dmg = DOWNLOADS_DIR / "AI-CLI-Orchestrator-Setup.dmg"
        if macos_dmg.exists():
            downloads["macos"] = {
                "url": "/downloads/AI-CLI-Orchestrator-Setup.dmg",
                "size": os.path.getsize(macos_dmg),
                "available": True
            }
            checksums["macos"] = "sha256:pending"
        else:
            downloads["macos"] = {"available": False}
        
        # Check for Linux installer
        linux_appimage = DOWNLOADS_DIR / "AI-CLI-Orchestrator-Setup.AppImage"
        if linux_appimage.exists():
            downloads["linux"] = {
                "url": "/downloads/AI-CLI-Orchestrator-Setup.AppImage",
                "size": os.path.getsize(linux_appimage),
                "available": True
            }
            checksums["linux"] = "sha256:pending"
        else:
            downloads["linux"] = {"available": False}
    else:
        downloads = {
            "windows": {"available": False},
            "macos": {"available": False},
            "linux": {"available": False}
        }
    
    return {
        "version": "1.0.0",
        "release_date": "2026-05-16",
        "downloads": downloads,
        "checksums": checksums,
        "release_notes": "Initial release of AI CLI Orchestrator with smart bootstrapper for AI CLI tools",
        "features": [
            "Unified interface for multiple AI CLI tools",
            "Smart dependency management",
            "Automatic workspace initialization",
            "Cross-platform support (Windows, macOS, Linux)"
        ]
    }


@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "server": "running",
        "clis": [],
        "session": None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

# Made with Bob
