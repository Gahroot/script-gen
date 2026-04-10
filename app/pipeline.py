import logging
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.generator import (
    check_compatibility,
    generate_scripts,
    regenerate_hooks,
    regenerate_meats,
    verify_hooks,
    verify_meats,
)
from app.schemas import GeneratedScripts, IntakeData

logger = logging.getLogger(__name__)


def _collect_failed_reasons(
    result: dict, index_key: str, reasons: list[str]
) -> tuple[list[int], list[str]]:
    """Extract failed indices and pair them with reasons."""
    failed = result.get(index_key, [])
    if not failed:
        return [], []

    result_reasons = result.get("reasons", [])
    paired_reasons = []
    for i, idx in enumerate(failed):
        if i < len(result_reasons):
            paired_reasons.append(result_reasons[i])
        else:
            paired_reasons.append("No specific reason provided")

    return failed, paired_reasons


def run_pipeline(data: IntakeData) -> GeneratedScripts:
    # Stage 1: Generate initial scripts
    scripts = generate_scripts(data)
    logger.info(
        "Generated %d hooks, %d meats, %d CTAs",
        len(scripts.hooks),
        len(scripts.meats),
        len(scripts.ctas),
    )

    max_loops = settings.max_regeneration_loops
    loop = 0
    prev_failure_signature: tuple | None = None
    while loop < max_loops:
        loop += 1
        logger.info("=== Verification loop %d/%d ===", loop, max_loops)
        needs_regen = False

        # Stage 2+3: Verify hooks and meats in parallel (independent calls)
        with ThreadPoolExecutor(max_workers=2) as ex:
            hook_future = ex.submit(verify_hooks, scripts, data)
            meat_future = ex.submit(verify_meats, scripts, data)
            hook_result = hook_future.result()
            meat_result = meat_future.result()

        failed_hooks, hook_reasons = _collect_failed_reasons(
            hook_result, "failed_hook_indices", hook_result.get("reasons", [])
        )
        failed_meats, meat_reasons = _collect_failed_reasons(
            meat_result, "failed_meat_indices", meat_result.get("reasons", [])
        )

        # Regenerate failed hooks and meats in parallel (independent calls)
        with ThreadPoolExecutor(max_workers=2) as ex:
            new_hooks_future = (
                ex.submit(regenerate_hooks, scripts, data, failed_hooks, hook_reasons)
                if failed_hooks
                else None
            )
            new_meats_future = (
                ex.submit(regenerate_meats, scripts, data, failed_meats, meat_reasons)
                if failed_meats
                else None
            )

            if new_hooks_future is not None:
                logger.info(
                    "Hook verification failed: %d hooks need regen", len(failed_hooks)
                )
                new_hooks = new_hooks_future.result()
                for i, idx in enumerate(failed_hooks):
                    if i < len(new_hooks) and 0 <= idx < len(scripts.hooks):
                        scripts.hooks[idx] = new_hooks[i]
                needs_regen = True

            if new_meats_future is not None:
                logger.info(
                    "Meat verification failed: %d meats need regen", len(failed_meats)
                )
                new_meats = new_meats_future.result()
                for i, idx in enumerate(failed_meats):
                    if i < len(new_meats) and 0 <= idx < len(scripts.meats):
                        scripts.meats[idx] = new_meats[i]
                needs_regen = True

        # Stage 4: Compatibility check (runs after hooks/meats are settled)
        compat_result = check_compatibility(scripts, data)
        compat_failed, compat_reasons = _collect_failed_reasons(
            compat_result, "failed_hook_indices", compat_result.get("reasons", [])
        )

        if compat_failed:
            logger.info(
                "Compatibility check failed: %d hooks incompatible", len(compat_failed)
            )
            new_hooks = regenerate_hooks(scripts, data, compat_failed, compat_reasons)
            for i, idx in enumerate(compat_failed):
                if i < len(new_hooks) and 0 <= idx < len(scripts.hooks):
                    scripts.hooks[idx] = new_hooks[i]
            needs_regen = True

        if not needs_regen:
            logger.info("All verification checks passed on loop %d", loop)
            break

        failure_signature = (
            tuple(sorted(failed_hooks)),
            tuple(sorted(failed_meats)),
            tuple(sorted(compat_failed)),
        )
        if failure_signature == prev_failure_signature:
            logger.warning(
                "Oscillation detected on loop %d — same indices failing twice. "
                "Accepting current scripts.",
                loop,
            )
            break
        prev_failure_signature = failure_signature
    else:
        logger.warning(
            "Max regeneration loops (%d) reached. Returning best-effort scripts.",
            max_loops,
        )

    return scripts
