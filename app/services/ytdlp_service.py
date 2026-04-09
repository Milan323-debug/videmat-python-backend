import yt_dlp
import os
import base64
import asyncio
from pathlib import Path
from typing import Optional, Callable
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
COOKIES_DIR = BASE_DIR / "cookies"
COOKIES_FILE = COOKIES_DIR / "youtube.txt"

DOWNLOADS_DIR.mkdir(exist_ok=True)
COOKIES_DIR.mkdir(exist_ok=True)

# ── Cookie Setup ─────────────────────────────────────────
def setup_cookies() -> Optional[str]:
    """
    Load cookies from local file or base64 env variable.
    Returns path to cookie file or None.
    """
    # Option A — local file (Windows dev)
    if COOKIES_FILE.exists():
        print(f"🍪 Using local cookie file: {COOKIES_FILE}")
        return str(COOKIES_FILE)

    # Option B — base64 env (Render)
    b64 = os.getenv("YOUTUBE_COOKIES_B64", "").strip()
    if b64:
        try:
            decoded = base64.b64decode(b64).decode("utf-8")
            COOKIES_FILE.write_text(decoded, encoding="utf-8")
            size = len(decoded)
            print(f"🍪 Cookie file written from env: {COOKIES_FILE} ({size} bytes)")
            if size < 100:
                print("⚠️  Cookie file seems too small!")
            return str(COOKIES_FILE)
        except Exception as e:
            print(f"❌ Failed to decode cookies: {e}")

    print("⚠️  No cookies configured — YouTube may block requests")
    return None

COOKIES_PATH = setup_cookies()

# ── Build yt-dlp options ─────────────────────────────────
def base_ydl_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "noplaylist": True,
        
        # ⚠️ Aggressive anti-blocking config for Render
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 60,
        "skip_unavailable_fragments": True,
        
        # Force IPv4 (YouTube blocks IPv6 more than IPv4)
        "force_ipv4": True,
        
        # Multiple player clients to bypass detection
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "tv", "mweb"],
                "skip": ["hls", "dash"],
            }
        },

        # Realistic browser headers to avoid bot detection
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "http_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        },
        
        # Reduce load
        "ratelimit": 100000,  # 100KB/s limit
        "sleep_interval": 1,
        "max_sleep_interval": 5,
    }

    # Add cookies
    if COOKIES_PATH and Path(COOKIES_PATH).exists():
        opts["cookiefile"] = COOKIES_PATH
        print(f"🍪 yt-dlp using cookies: {COOKIES_PATH}")
    else:
        print(f"⚠️  No cookies - YouTube may block!")

    # Add proxy if set (e.g., from Bright Data, Oxylabs, etc.)
    proxy = os.getenv("PROXY_URL", "").strip()
    if proxy:
        opts["proxy"] = proxy
        opts["socket_timeout"] = 60  # Proxy needs more time
        print(f"🌐 Using proxy: {proxy[:30]}...")
    
    return opts

# ── Fetch video info ─────────────────────────────────────
async def get_video_info(url: str) -> dict:
    """Fetch video metadata using yt-dlp."""

    def _fetch():
        opts = base_ydl_opts()
        opts["skip_download"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info

    # Run blocking yt-dlp in thread pool
    loop = asyncio.get_event_loop()
    try:
        raw = await loop.run_in_executor(None, _fetch)
    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        print(f"yt-dlp error: {err}")
        if "Sign in" in err or "bot" in err.lower():
            raise ValueError("RATE_LIMITED")
        if "unavailable" in err:
            raise ValueError("VIDEO_UNAVAILABLE")
        if "Private" in err:
            raise ValueError("VIDEO_PRIVATE")
        if "copyright" in err:
            raise ValueError("VIDEO_COPYRIGHT")
        if "429" in err or "blocked" in err.lower():
            raise ValueError("RATE_LIMITED")
        raise ValueError(f"FETCH_FAILED: {err[:100]}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise ValueError(f"FETCH_FAILED: {str(e)[:100]}")

    return parse_video_info(raw)

def parse_video_info(raw: dict) -> dict:
    options = build_download_options(raw.get("formats", []), raw.get("duration", 0))
    return {
        "id": raw.get("id", ""),
        "title": raw.get("title", "Unknown"),
        "thumbnail": raw.get("thumbnail", ""),
        "duration": raw.get("duration", 0),
        "uploader": raw.get("uploader", "Unknown"),
        "view_count": raw.get("view_count", 0),
        "description": (raw.get("description") or "")[:300],
        "options": options,
    }

def build_download_options(formats: list, duration: int) -> list:
    options = []
    heights = [1080, 720, 480, 360, 240, 144]

    for height in heights:
        options.append({
            "id": f"video_{height}p",
            "label": f"{height}p HD" if height >= 720 else f"{height}p",
            "type": "video",
            "quality": f"{height}p",
            "format": f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best[height<={height}]",
            "ext": "mp4",
            "filesize": estimate_video_size(height, duration),
            "icon": "🎬" if height >= 720 else "📹",
        })

    options.append({
        "id": "audio_mp3_128",
        "label": "MP3 — 128 kbps",
        "type": "audio",
        "quality": "128kbps",
        "format": "bestaudio/best",
        "ext": "mp3",
        "filesize": estimate_audio_size(128, duration),
        "icon": "🎵",
    })

    options.append({
        "id": "audio_mp3_320",
        "label": "MP3 — 320 kbps",
        "type": "audio",
        "quality": "320kbps",
        "format": "bestaudio/best",
        "ext": "mp3",
        "filesize": estimate_audio_size(320, duration),
        "icon": "🎵",
    })

    return options

def estimate_video_size(height: int, duration: int) -> int:
    kbps = {1080: 4000, 720: 2500, 480: 1200, 360: 700, 240: 400, 144: 200}
    return int((kbps.get(height, 500) * 1000 / 8) * duration)

def estimate_audio_size(kbps: int, duration: int) -> int:
    return int((kbps * 1000 / 8) * duration)

# ── Download file ────────────────────────────────────────
async def download_file(
    url: str,
    fmt: str,
    output_path: str,
    ext: str,
    on_progress: Optional[Callable] = None,
) -> str:
    """Download video/audio to output_path, calling on_progress(pct) periodically."""

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0 and on_progress:
                pct = (downloaded / total) * 100
                on_progress(round(pct, 1))

    def _download():
        is_audio = ext == "mp3"

        opts = base_ydl_opts()
        opts.update({
            "format": fmt,
            "outtmpl": output_path,
            "progress_hooks": [progress_hook],
            "merge_output_format": "mp4" if not is_audio else None,
        })

        if is_audio:
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        return output_path

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _download)
        return result
    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        if "Sign in" in err or "429" in err:
            raise ValueError("RATE_LIMITED")
        raise ValueError(f"DOWNLOAD_FAILED: {err}")
