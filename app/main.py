from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_db, close_db
from app.routes import info, download, history
import os
import sys

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(
    title="YouTube Downloader API",
    description="Download YouTube videos and audio",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "YouTube Downloader API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {"status": "ok", "platform": sys.platform}

@app.get("/debug/cookies")
async def debug_cookies():
    from pathlib import Path
    import os
    cookie_path = Path(__file__).parent.parent / "cookies" / "youtube.txt"
    b64_env = os.getenv("YOUTUBE_COOKIES_B64", "")
    return {
        "cookie_file_exists": cookie_path.exists(),
        "cookie_file_size": cookie_path.stat().st_size if cookie_path.exists() else 0,
        "b64_env_set": bool(b64_env),
        "b64_env_length": len(b64_env),
        "proxy_set": bool(os.getenv("PROXY_URL")),
    }

app.include_router(info.router, prefix="/api/info", tags=["Info"])
app.include_router(download.router, prefix="/api/stream", tags=["Download"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
