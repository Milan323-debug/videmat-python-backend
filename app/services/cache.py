import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Job:
    id: str
    status: str = "pending"
    progress: float = 0.0
    file_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

# In-memory store — fast for polling
_jobs: Dict[str, Job] = {}

def create_job(job_id: str) -> Job:
    job = Job(id=job_id)
    _jobs[job_id] = job
    return job

def update_job(job_id: str, **kwargs) -> Optional[Job]:
    job = _jobs.get(job_id)
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
    return job

def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)

async def schedule_cleanup(job_id: str, file_path: Optional[str], delay: int = 3600):
    """Delete job and temp file after delay seconds."""
    await asyncio.sleep(delay)
    _jobs.pop(job_id, None)
    if file_path:
        import os
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")
