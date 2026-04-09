from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from app.models import VideoInfoRequest
from app.services.ytdlp_service import get_video_info
from app.database import videocache_collection
import re

router = APIRouter()

YOUTUBE_REGEX = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}'
)

ERROR_MAP = {
    "RATE_LIMITED": (429, "YouTube is blocking this server. Please try again later."),
    "VIDEO_UNAVAILABLE": (404, "This video is unavailable or removed."),
    "VIDEO_PRIVATE": (403, "This video is private."),
    "VIDEO_COPYRIGHT": (451, "Blocked due to copyright restrictions."),
    "FETCH_FAILED": (502, "Could not fetch video info. Try again."),
    "PARSE_FAILED": (500, "Failed to parse video data."),
}

@router.post("/")
async def fetch_video_info(body: VideoInfoRequest):
    url = body.url.strip()

    if not YOUTUBE_REGEX.match(url):
        raise HTTPException(400, "Invalid YouTube URL.")

    # ── Check MongoDB cache ───────────────────────────────
    cached = await videocache_collection.find_one({"url": url})
    if cached:
        # Cache valid for 30 minutes
        age = datetime.utcnow() - cached["cached_at"]
        if age < timedelta(minutes=30):
            print(f"⚡ Cache hit: {url}")
            return {"success": True, "data": cached["data"], "from_cache": True}
        else:
            # Expired — delete it
            await videocache_collection.delete_one({"url": url})

    # ── Fetch from yt-dlp ─────────────────────────────────
    print(f"🌐 Fetching: {url}")
    try:
        info = await get_video_info(url)
    except ValueError as e:
        code, message = ERROR_MAP.get(str(e), (500, "Something went wrong."))
        raise HTTPException(code, message)
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(500, "Unexpected error fetching video.")

    # ── Save to MongoDB cache ─────────────────────────────
    await videocache_collection.insert_one({
        "url": url,
        "video_id": info["id"],
        "data": info,
        "cached_at": datetime.utcnow(),
    })

    return {"success": True, "data": info, "from_cache": False}
