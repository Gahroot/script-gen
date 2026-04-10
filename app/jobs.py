import threading
import time
import uuid
from dataclasses import dataclass, field

from app.schemas import IntakeData, JobStatus


@dataclass
class Job:
    job_id: str
    intake: IntakeData
    status: JobStatus = JobStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    markdown: str | None = None
    error: str | None = None
    email_sent: bool = False


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, intake: IntakeData) -> Job:
        job = Job(job_id=str(uuid.uuid4()), intake=intake)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)


store = JobStore()
