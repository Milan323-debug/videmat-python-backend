# YouTube Downloader API — Python Backend

A FastAPI backend for downloading YouTube videos and audio with async processing and MongoDB caching.

## Project Structure

```
python-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              ← FastAPI app entry
│   ├── database.py          ← MongoDB connection
│   ├── models.py            ← Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── info.py          ← fetch video info
│   │   ├── download.py      ← start/poll/serve downloads
│   │   └── history.py       ← download history
│   └── services/
│       ├── __init__.py
│       ├── ytdlp_service.py ← yt-dlp wrapper
│       └── cache.py         ← in-memory job cache
├── cookies/                 ← YouTube cookies (gitignored)
├── downloads/               ← temp files (gitignored)
├── requirements.txt
├── render.yaml
├── .env
└── .gitignore
```

## Setup

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Environment

Copy your MongoDB URI and YouTube cookies to `.env`:

```env
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/ytdownloader
YOUTUBE_COOKIES_B64=<base64 encoded cookies>
PROXY_URL=  # Optional
PORT=8000
```

### 3. Get YouTube Cookies

See the main README in the parent `vidmate-backend` folder for how to export and encode cookies.

### 4. Run Locally

```powershell
uvicorn app.main:app --reload --port 8000
```

Access the interactive API docs at: **http://localhost:8000/docs**

## API Endpoints

### Get Video Info
```powershell
$body = '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
Invoke-RestMethod -Method POST `
  -Uri http://localhost:8000/api/info/ `
  -ContentType "application/json" `
  -Body $body
```

### Start Download
```powershell
$body = '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","format_id":"video_720p","ext":"mp4","quality":"720p","title":"Example Video","video_id":"jNQXAC9IVRw"}'
Invoke-RestMethod -Method POST `
  -Uri http://localhost:8000/api/stream/start `
  -ContentType "application/json" `
  -Body $body
```

### Get Download Status
```powershell
Invoke-RestMethod -Method GET `
  -Uri http://localhost:8000/api/stream/status/{job_id}
```

### Download File
```powershell
Invoke-WebRequest -Method GET `
  -Uri http://localhost:8000/api/stream/file/{job_id} `
  -OutFile "video.mp4"
```

### Get History
```powershell
Invoke-RestMethod -Method GET `
  -Uri http://localhost:8000/api/history/?page=1&limit=20
```

## Why Python?

- ✅ No binary PATH issues on Render
- ✅ yt-dlp works reliably in virtualenv
- ✅ FastAPI is super clean & fast
- ✅ Motor for async MongoDB
- ✅ Better error handling & debugging

## Deploy to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set Build Command: `pip install -r requirements.txt`
4. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (see `.env` template)
6. Deploy!

## Debugging

Check cookies are loading:
```bash
curl https://your-render-url.onrender.com/debug/cookies
```

## Next Steps

- Copy fresh YouTube cookies to `YOUTUBE_COOKIES_B64` env var
- Test locally first with `uvicorn`
- Deploy to Render
- Monitor logs for any issues
