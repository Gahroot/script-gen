import logging
from pathlib import Path

import resend

from app.config import settings
from app.schemas import IntakeData

logger = logging.getLogger(__name__)

FILMING_TIPS_PATH = Path(__file__).resolve().parent.parent / "Filming Tips.png"


def is_enabled() -> bool:
    return bool(settings.resend_api_key)


def send_scripts(intake: IntakeData, markdown: str) -> bool:
    if not is_enabled():
        logger.info("Resend not configured — skipping email delivery")
        return False

    resend.api_key = settings.resend_api_key

    subject = f"Your 300 {intake.business_name} ad scripts are ready"
    html = _render_html(intake)

    attachments: list[resend.Attachment] = [_scripts_attachment(intake, markdown)]
    filming_tips = _load_filming_tips()
    if filming_tips is not None:
        attachments.append(filming_tips)

    params: resend.Emails.SendParams = {
        "from": settings.resend_from_email,
        "to": [intake.contact_email],
        "subject": subject,
        "html": html,
        "attachments": attachments,
    }

    response = resend.Emails.send(params)
    logger.info(
        "Sent scripts to %s (resend id: %s)",
        intake.contact_email,
        response.get("id", "unknown"),
    )
    return True


def _load_filming_tips() -> resend.Attachment | None:
    if not FILMING_TIPS_PATH.is_file():
        logger.warning("Filming Tips image not found at %s", FILMING_TIPS_PATH)
        return None
    return {
        "filename": "Filming Tips.png",
        "content": list(FILMING_TIPS_PATH.read_bytes()),
        "content_type": "image/png",
    }


def _scripts_attachment(intake: IntakeData, markdown: str) -> resend.Attachment:
    slug = "".join(
        c if c.isalnum() or c in ("-", "_") else "-"
        for c in intake.business_name.lower().replace(" ", "-")
    ).strip("-")
    filename = f"{slug}-300-scripts.md"
    return {
        "filename": filename,
        "content": list(markdown.encode("utf-8")),
        "content_type": "text/markdown",
    }


def _render_html(intake: IntakeData) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, system-ui, sans-serif; max-width: 640px; margin: 0 auto; padding: 24px; color: #111; line-height: 1.55;">
<p>Hi {intake.contact_name},</p>

<p>Attached you will find the scripts ready to paste into your teleprompter!</p>

<p><strong>Record everything in ONE take. Do not stop the camera until you are completely done!</strong></p>

<h3 style="margin-top: 28px;">1. The Pattern</h3>
<p>For every single line, do this:</p>
<ul>
  <li>Say the number (Example: "Hook 1")</li>
  <li>Read the words on your screen.</li>
  <li>Wait 2 seconds in silence before the next one.</li>
</ul>

<h3 style="margin-top: 28px;">2. If You Mess Up</h3>
<p>Do not stop the video. Just breathe and start that specific line over.</p>
<p>Example: "Hook 11... [messed up]"...(RESET)... "Hook 11... [read it right this time]."</p>

<p style="margin-top: 28px;">Filming tips are attached as <strong>Filming Tips.png</strong>.</p>

<p>I also filmed this quick video with some tips and an example of me filming my own ads:<br>
<a href="https://youtu.be/16yB4aqHugw">https://youtu.be/16yB4aqHugw</a></p>

<p>If you have any questions, please let me know!</p>

<p>- Nolan</p>
</body>
</html>"""
