"""End-to-end reliability wrappers for the generation pipeline and email delivery.

Patterns borrowed from khoj-ai/khoj and databricks product-search (tenacity
@retry decorator + Retrying iterator with before_sleep_log). The goal is that
a submission either fully succeeds (scripts generated, verified, delivered) or
fails loudly after exhausting retries — never a silent partial success.
"""

import logging

from tenacity import (
    Retrying,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app import email_delivery
from app.pipeline import run_pipeline
from app.schemas import GeneratedScripts, IntakeData

logger = logging.getLogger(__name__)

EXPECTED_HOOKS = 50
EXPECTED_MEATS = 3
EXPECTED_CTAS = 2
MIN_MARKDOWN_LENGTH = 500

PIPELINE_ATTEMPTS = 2
EMAIL_ATTEMPTS = 3


class ScriptsIncompleteError(RuntimeError):
    """Generated scripts don't match the expected shape."""


class MarkdownEmptyError(RuntimeError):
    """Formatter produced no usable markdown."""


class EmailDeliveryError(RuntimeError):
    """Email delivery failed after all retries."""


def _assert_scripts_complete(scripts: GeneratedScripts) -> None:
    problems: list[str] = []
    if len(scripts.hooks) != EXPECTED_HOOKS:
        problems.append(f"hooks={len(scripts.hooks)} (expected {EXPECTED_HOOKS})")
    if len(scripts.meats) != EXPECTED_MEATS:
        problems.append(f"meats={len(scripts.meats)} (expected {EXPECTED_MEATS})")
    if len(scripts.ctas) != EXPECTED_CTAS:
        problems.append(f"ctas={len(scripts.ctas)} (expected {EXPECTED_CTAS})")
    for i, hook in enumerate(scripts.hooks):
        if not hook or not hook.strip():
            problems.append(f"hook[{i}] empty")
    for i, meat in enumerate(scripts.meats):
        if not meat or not meat.strip():
            problems.append(f"meat[{i}] empty")
    for i, cta in enumerate(scripts.ctas):
        if not cta or not cta.strip():
            problems.append(f"cta[{i}] empty")
    if problems:
        raise ScriptsIncompleteError(
            "Generated scripts are incomplete: " + "; ".join(problems)
        )


def assert_markdown_nonempty(markdown: str) -> None:
    if not markdown or len(markdown.strip()) < MIN_MARKDOWN_LENGTH:
        raise MarkdownEmptyError(
            f"Markdown output suspiciously short: "
            f"{len(markdown or '')} chars (min {MIN_MARKDOWN_LENGTH})"
        )


def generate_scripts_reliably(intake: IntakeData, job_id: str) -> GeneratedScripts:
    """Run the pipeline with retry + shape verification.

    Raises the final exception if every attempt fails.
    """
    for attempt in Retrying(
        stop=stop_after_attempt(PIPELINE_ATTEMPTS),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    ):
        with attempt:
            attempt_number = attempt.retry_state.attempt_number
            logger.info(
                "Job %s: pipeline attempt %d/%d",
                job_id,
                attempt_number,
                PIPELINE_ATTEMPTS,
            )
            scripts = run_pipeline(intake)
            _assert_scripts_complete(scripts)
            logger.info(
                "Job %s: pipeline attempt %d succeeded (%d hooks, %d meats, %d ctas)",
                job_id,
                attempt_number,
                len(scripts.hooks),
                len(scripts.meats),
                len(scripts.ctas),
            )
            return scripts

    raise RuntimeError("unreachable: Retrying(reraise=True) raises on final failure")


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    stop=stop_after_attempt(EMAIL_ATTEMPTS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _send_scripts_with_retry(intake: IntakeData, markdown: str) -> bool:
    return email_delivery.send_scripts(intake, markdown)


def send_email_reliably(intake: IntakeData, markdown: str, job_id: str) -> bool:
    """Deliver the scripts email with retries.

    Returns True if delivered, False if email delivery is disabled in config.
    Raises EmailDeliveryError if delivery is enabled but fails every attempt.
    """
    if not email_delivery.is_enabled():
        logger.info("Job %s: email delivery disabled, skipping", job_id)
        return False

    try:
        sent = _send_scripts_with_retry(intake, markdown)
    except Exception as e:
        logger.exception("Job %s: email delivery failed after all retries", job_id)
        raise EmailDeliveryError(
            f"Email delivery failed after {EMAIL_ATTEMPTS} attempts: {e}"
        ) from e

    if not sent:
        raise EmailDeliveryError(
            "send_scripts returned False despite email delivery being enabled"
        )

    logger.info("Job %s: email delivered to %s", job_id, intake.contact_email)
    return True
