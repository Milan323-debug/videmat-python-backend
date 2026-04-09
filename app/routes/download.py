from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime
import uuid
import asyncio
import os

from app.models import DownloadStartRequest
from app.services.ytdlp_service import download_file, DOWNLOADS_DIR
from app.services.cache import create_job, update_job, get_job, schedule_cleanup
from app.database import history_collection

router = APIRouter()

# ── POST /api/stream/start ───────────────────────────────
@router.post("/start")
async def start_download(body: DownloadStartRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    safe_ext = body.ext if body.ext in ["mp4", "mp3", "webm"] else "mp4"
    safe_name = "".join(c for c in body.title if c.isalnum() or c in " _-")[:60]
    output = str(DOWNLOADS_DIR / f"{job_id}_{safe_name}.{safe_ext}")

    create_job(job_id)

    # Run download in background
    background_tasks.add_task(
        run_download,
        job_id, body.url, body.format_id,
        output, safe_ext, body
    )

    return {"success": True, "job_id": job_id}

async def run_download(job_id, url, fmt, output_path, ext, meta):
    def on_progress(pct):
        update_job(job_id, status="downloading", progress=pct)

    try:
        update_job(job_id, status="downloading", progress=0)
        file_path = await download_file(url, fmt, output_path, ext, on_progress)

        update_job(job_id, status="done", progress=100, file_path=file_path)

        # Save to MongoDB history
        await history_collection.insert_one({
            "job_id": job_id,
            "url": url,
            "video_id": meta.video_id,
            "title": meta.title,
            "thumbnail": meta.thumbnail,
            "uploader": meta.uploader,
            "duration": meta.duration,
            "quality": meta.quality,
            "ext": ext,
            "filesize": meta.filesize,
            "type": meta.type,
            "created_at": datetime.utcnow(),
        })

        print(f"✅ Job {job_id} complete")

        # Schedule cleanup after 1 hour
        asyncio.create_task(schedule_cleanup(job_id, file_path, 3600))

    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        update_job(job_id, status="error", error=str(e))

# ── GET /api/stream/status/:job_id ───────────────────────
@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found or expired.")
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
    }

# ── GET /api/stream/file/:job_id ─────────────────────────
@router.get("/file/{job_id}")
async def serve_file(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(404, "Job not found or expired.")
    if job.status in ("pending", "downloading"):
        raise HTTPException(202, "File not ready yet.")
    if job.status == "error":
        raise HTTPException(500, job.error or "Download failed.")
    if not job.file_path or not Path(job.file_path).exists():
        raise HTTPException(410, "File expired or deleted.")

    ext = Path(job.file_path).suffix.lower()
    mime_map = {".mp4": "video/mp4", ".mp3": "audio/mpeg", ".webm": "video/webm"}
    media = mime_map.get(ext, "application/octet-stream")

    return FileResponse(
        path=job.file_path,
        media_type=media,
        filename=Path(job.file_path).name,
        headers={"Accept-Ranges": "bytes"},
    )
