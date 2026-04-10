import logging
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app import email_delivery
from app.config import settings
from app.formatter import format_markdown
from app.jobs import store
from app.reliability import (
    EmailDeliveryError,
    assert_markdown_nonempty,
    generate_scripts_reliably,
    send_email_reliably,
)
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

    # Stage 1: generate + verify scripts with retry. Hard failure here =
    # job FAILED (nothing usable was produced).
    try:
        scripts = generate_scripts_reliably(job.intake, job_id)
        markdown = format_markdown(scripts, job.intake)
        assert_markdown_nonempty(markdown)
    except Exception as e:
        logger.exception(
            "Job %s: script generation failed for %s", job_id, job.intake.business_name
        )
        store.update(
            job_id,
            status=JobStatus.FAILED,
            error=f"Script generation failed: {e}",
            completed_at=time.time(),
        )
        return

    # Persist markdown immediately so /jobs/{id} can return it even if
    # email delivery blows up below.
    store.update(job_id, markdown=markdown)

    # Stage 2: email delivery with retry. If this fails after every retry,
    # the job is still COMPLETED — the scripts are ready and fetchable —
    # but email_sent=False and the email error is stored for visibility.
    email_sent = False
    email_error: str | None = None
    try:
        email_sent = send_email_reliably(job.intake, markdown, job_id)
    except EmailDeliveryError as e:
        email_error = str(e)
    except Exception as e:
        logger.exception("Job %s: unexpected email error", job_id)
        email_error = f"Unexpected email error: {e}"

    store.update(
        job_id,
        status=JobStatus.COMPLETED,
        markdown=markdown,
        completed_at=time.time(),
        email_sent=email_sent,
        error=email_error,
    )
    logger.info(
        "Job %s completed for %s (email_sent=%s)",
        job_id,
        job.intake.business_name,
        email_sent,
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
