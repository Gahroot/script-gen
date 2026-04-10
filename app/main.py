import logging
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app import email_delivery
from app.config import settings
from app.formatter import format_markdown
from app.jobs import store
from app.pipeline import run_pipeline
from app.schemas import (
    IntakeData,
    JobCreateResponse,
    JobStatus,
    JobStatusResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Script Gen",
    description="Batch ad script generation pipeline — 50 hooks × 3 meats × 2 CTAs = 300 ads",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_job(job_id: str) -> None:
    job = store.get(job_id)
    if job is None:
        logger.error("Job %s vanished before execution", job_id)
        return

    store.update(job_id, status=JobStatus.RUNNING)
    logger.info("Starting job %s for %s", job_id, job.intake.business_name)

    try:
        scripts = run_pipeline(job.intake)
        markdown = format_markdown(scripts, job.intake)

        email_sent = False
        try:
            email_sent = email_delivery.send_scripts(job.intake, markdown)
        except Exception:
            logger.exception("Email delivery failed for job %s", job_id)

        store.update(
            job_id,
            status=JobStatus.COMPLETED,
            markdown=markdown,
            completed_at=time.time(),
            email_sent=email_sent,
        )
        logger.info("Job %s completed for %s", job_id, job.intake.business_name)
    except Exception as e:
        logger.exception("Job %s failed for %s", job_id, job.intake.business_name)
        store.update(
            job_id,
            status=JobStatus.FAILED,
            error=str(e),
            completed_at=time.time(),
        )


@app.post("/generate", response_model=JobCreateResponse, status_code=202)
async def generate(
    data: IntakeData,
    background_tasks: BackgroundTasks,
    request: Request,
) -> JobCreateResponse:
    job = store.create(data)
    background_tasks.add_task(_run_job, job.job_id)
    logger.info("Queued job %s for %s", job.job_id, data.business_name)

    status_url = str(request.url_for("get_job", job_id=job.job_id))

    return JobCreateResponse(
        job_id=job.job_id,
        status=job.status,
        status_url=status_url,
        business_name=data.business_name,
        email_delivery=email_delivery.is_enabled(),
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse, name="get_job")
async def get_job(job_id: str) -> JobStatusResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    duration = (
        job.completed_at - job.created_at if job.completed_at is not None else None
    )
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        business_name=job.intake.business_name,
        contact_email=job.intake.contact_email,
        created_at=job.created_at,
        completed_at=job.completed_at,
        duration_seconds=duration,
        email_sent=job.email_sent,
        markdown=job.markdown,
        error=job.error,
    )


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "email_delivery": email_delivery.is_enabled(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
