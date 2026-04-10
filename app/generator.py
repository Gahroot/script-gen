import json
import logging
import re
import time

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import settings
from app.prompts import (
    COMPATIBILITY_CHECK_PROMPT,
    GENERATION_PROMPT,
    PLAYBOOK_RULES,
    REGENERATE_HOOKS_PROMPT,
    REGENERATE_MEATS_PROMPT,
    VERIFY_HOOKS_PROMPT,
    VERIFY_MEATS_PROMPT,
)
from app.schemas import GeneratedScripts, IntakeData

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.gemini_api_key)

MAX_RETRIES = 4
BASE_DELAY = 10  # seconds
MAX_DELAY = 30  # cap per-attempt sleep so total budget is ~10+20+30+30 = 90s


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=1.0,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return response.text
        except APIError as e:
            last_error = e
            if e.code in (429, 503):
                delay = min(BASE_DELAY * attempt, MAX_DELAY)
                logger.warning(
                    "Retryable error %s (attempt %d/%d): %s. Waiting %ds...",
                    e.code,
                    attempt,
                    MAX_RETRIES,
                    e,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error("Non-retryable Gemini error: %s", e)
                raise
    raise RuntimeError(
        f"Gemini still failing after {MAX_RETRIES} retries. Last error: {last_error}"
    )


_LABEL_PREFIX_RE = re.compile(
    r'^\s*["\'`]?\s*(?:hook|meat|cta)\s*\d+\s*[:\-–—]\s*["\'`]?\s*',
    re.IGNORECASE,
)

_LABEL_ANYWHERE_RE = re.compile(
    r'["\'`]?\b(?:hook|meat|cta)\s*\d+\s*[:\-–—]\s*["\'`]?\s*',
    re.IGNORECASE,
)


def _strip_label_prefix(text: str) -> str:
    cleaned = _LABEL_PREFIX_RE.sub("", text)
    cleaned = _LABEL_ANYWHERE_RE.sub("", cleaned)
    return cleaned.strip()


def _sanitize_list(items: list[str]) -> list[str]:
    return [_strip_label_prefix(item) for item in items]


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def _format_intake(data: IntakeData) -> dict:
    pain_points_solutions = "\n".join(
        f"- Pain Point {i + 1}: {ps.pain_point}\n  Solution {i + 1}: {ps.solution}"
        for i, ps in enumerate(data.pain_points_solutions)
    )
    top_stats = "\n".join(f"- {stat}" for stat in data.top_stats)
    city_service_area = (
        " / ".join(filter(None, [data.city, data.service_area])) or "N/A"
    )

    return {
        "business_name": data.business_name,
        "target_audience": data.target_audience,
        "city_service_area": city_service_area,
        "pain_points_solutions": pain_points_solutions,
        "offer": data.offer,
        "risk_reversal": data.risk_reversal or "N/A",
        "guarantees": data.guarantees or "N/A",
        "limited_availability": data.limited_availability or "N/A",
        "discounts": data.discounts or "N/A",
        "lead_magnet": data.lead_magnet or "N/A",
        "top_stats": top_stats,
        "landing_page_url": data.landing_page_url or "N/A",
    }


def _number_list(items: list[str], label: str) -> str:
    return "\n".join(f"{label} {i + 1}: {item}" for i, item in enumerate(items))


def generate_scripts(data: IntakeData) -> GeneratedScripts:
    formatted = _format_intake(data)
    prompt = GENERATION_PROMPT.format(**formatted)

    logger.info("Generating initial scripts for %s", data.business_name)
    raw = _call_gemini(PLAYBOOK_RULES, prompt)
    parsed = _parse_json(raw)

    return GeneratedScripts(
        hooks=_sanitize_list(parsed["hooks"]),
        meats=_sanitize_list(parsed["meats"]),
        ctas=_sanitize_list(parsed["ctas"]),
    )


def verify_hooks(scripts: GeneratedScripts, data: IntakeData) -> dict:
    formatted = _format_intake(data)
    prompt = VERIFY_HOOKS_PROMPT.format(
        count=len(scripts.hooks),
        business_name=data.business_name,
        target_audience=data.target_audience,
        top_stats=formatted["top_stats"],
        hooks_numbered=_number_list(scripts.hooks, "Hook"),
    )

    logger.info("Verifying %d hooks", len(scripts.hooks))
    raw = _call_gemini(PLAYBOOK_RULES, prompt)
    return _parse_json(raw)


def verify_meats(scripts: GeneratedScripts, data: IntakeData) -> dict:
    formatted = _format_intake(data)
    pain_points = "\n".join(f"- {ps.pain_point}" for ps in data.pain_points_solutions)
    prompt = VERIFY_MEATS_PROMPT.format(
        business_name=data.business_name,
        target_audience=data.target_audience,
        offer=data.offer,
        top_stats=formatted["top_stats"],
        pain_points=pain_points,
        meats_numbered=_number_list(scripts.meats, "Meat"),
    )

    logger.info("Verifying %d meats", len(scripts.meats))
    raw = _call_gemini(PLAYBOOK_RULES, prompt)
    return _parse_json(raw)


def check_compatibility(scripts: GeneratedScripts, data: IntakeData) -> dict:
    formatted = _format_intake(data)
    prompt = COMPATIBILITY_CHECK_PROMPT.format(
        business_name=data.business_name,
        top_stats=formatted["top_stats"],
        hooks_numbered=_number_list(scripts.hooks, "Hook"),
        meats_numbered=_number_list(scripts.meats, "Meat"),
    )

    logger.info("Checking hook-meat compatibility")
    raw = _call_gemini(PLAYBOOK_RULES, prompt)
    return _parse_json(raw)


def regenerate_hooks(
    scripts: GeneratedScripts,
    data: IntakeData,
    failed_indices: list[int],
    reasons: list[str],
) -> list[str]:
    formatted = _format_intake(data)

    passing_hooks = [h for i, h in enumerate(scripts.hooks) if i not in failed_indices]
    failed_hooks_with_reasons = "\n".join(
        f'- Hook {idx + 1} (FAILED): "{scripts.hooks[idx]}" — Reason: {reason}'
        for idx, reason in zip(failed_indices, reasons)
    )

    prompt = REGENERATE_HOOKS_PROMPT.format(
        business_name=data.business_name,
        target_audience=data.target_audience,
        city_service_area=" / ".join(filter(None, [data.city, data.service_area]))
        or "N/A",
        top_stats=formatted["top_stats"],
        passing_hooks="\n".join(f"- {h}" for h in passing_hooks),
        failed_hooks_with_reasons=failed_hooks_with_reasons,
        count=len(failed_indices),
    )

    logger.info("Regenerating %d failed hooks", len(failed_indices))
    raw = _call_gemini(PLAYBOOK_RULES, prompt)
    parsed = _parse_json(raw)
    return _sanitize_list(parsed["hooks"])


def regenerate_meats(
    scripts: GeneratedScripts,
    data: IntakeData,
    failed_indices: list[int],
    reasons: list[str],
) -> list[str]:
    formatted = _format_intake(data)

    failed_set = set(failed_indices)
    failed_meats_with_reasons = "\n".join(
        f'- Meat {idx + 1} (FAILED): "{scripts.meats[idx]}" — Reason: {reason}'
        for idx, reason in zip(failed_indices, reasons)
    )
    passing_meats = (
        "\n".join(
            f'- Meat {i + 1}: "{meat}"'
            for i, meat in enumerate(scripts.meats)
            if i not in failed_set
        )
        or "(none)"
    )

    prompt = REGENERATE_MEATS_PROMPT.format(
        business_name=data.business_name,
        target_audience=data.target_audience,
        city_service_area=" / ".join(filter(None, [data.city, data.service_area]))
        or "N/A",
        offer=data.offer,
        top_stats=formatted["top_stats"],
        pain_points_solutions=formatted["pain_points_solutions"],
        passing_meats=passing_meats,
        failed_meats_with_reasons=failed_meats_with_reasons,
        count=len(failed_indices),
    )

    logger.info("Regenerating %d failed meats", len(failed_indices))
    raw = _call_gemini(PLAYBOOK_RULES, prompt)
    parsed = _parse_json(raw)
    return _sanitize_list(parsed["meats"])
