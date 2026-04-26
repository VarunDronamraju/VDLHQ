import json
from pathlib import Path
from uuid import UUID
from dataclasses import dataclass
from typing import Optional, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import structlog

from app.models.core import CommunicationsLog
from app.services.ai import llm_client

logger = structlog.get_logger()
TEMPLATES_DIR = Path(__file__).parent / "templates"

TONE_REWRITE_SYSTEM = """You are a professional communications editor for a film location agency.
Rewrite the message below in a warm, professional tone.

RULES (strict):
- Do NOT change any facts, dates, names, prices, or instructions
- Do NOT add information that is not in the original
- Do NOT remove any information from the original
- Only adjust phrasing and tone
- If you cannot improve the tone without breaking the rules, return the original unchanged"""

@dataclass
class CommunicationResult:
    success: bool
    log_id: Optional[UUID]
    error: Optional[str] = None

async def send(
    template_name: str,
    template_data: Dict[str, Any],
    channel: str,
    db: AsyncSession,
    lead_id: Optional[UUID] = None,
    booking_id: Optional[UUID] = None,
    rewrite: bool = False,
) -> CommunicationResult:
    """
    Renders a template, optionally rewrites tone with AI, and logs the communication (A5).
    """
    log = logger.bind(template=template_name, channel=channel, lead_id=str(lead_id) if lead_id else None)
    
    # 1. Load and render template
    template_path = TEMPLATES_DIR / f"{template_name}.txt"
    if not template_path.exists():
        return CommunicationResult(success=False, log_id=None, error=f"Template not found: {template_name}")

    template = template_path.read_text()
    try:
        rendered = template.format(**template_data)
    except KeyError as e:
        return CommunicationResult(success=False, log_id=None, error=f"Missing template variable: {e}")

    message_body = rendered

    # 2. Optional LLM Tone Rewrite
    if rewrite:
        try:
            rewritten = await llm_client.call(
                messages=[{"role": "user", "content": f"Rewrite this message:\n\n{rendered}"}],
                system=TONE_REWRITE_SYSTEM,
                service_name="A5",
                lead_id=str(lead_id) if lead_id else None,
            )
            # Basic sanity check: rewrite shouldn't be too short
            if len(rewritten) >= len(rendered) * 0.5:
                message_body = rewritten
        except Exception as e:
            log.warning("tone_rewrite_failed", error=str(e))
            # Fallback to original rendered template

    # 3. Channel Stub (Internal only for now)
    send_success = await _send_via_channel(channel, template_data, message_body)

    # 4. Persistence
    log_entry = CommunicationsLog(
        lead_id=lead_id,
        booking_id=booking_id,
        template_name=template_name,
        channel=channel,
        status="sent" if send_success else "failed",
        error_detail=None if send_success else "Channel provider failure",
        sent_at=datetime.now(timezone.utc) if send_success else None
    )
    
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    log.info("communication_sent", log_id=str(log_entry.id), success=send_success)
    return CommunicationResult(success=send_success, log_id=log_entry.id)

async def _send_via_channel(channel: str, template_data: Dict[str, Any], body: str) -> bool:
    """
    Stubs for actual delivery providers (Email, WhatsApp).
    For now, we just log to console and return True.
    """
    recipient = template_data.get("email") or template_data.get("phone") or "Unknown"
    
    print(f"\n--- OUTBOUND MESSAGE ({channel.upper()}) ---")
    print(f"To: {recipient}")
    print(f"Body:\n{body}")
    print("-------------------------------------------\n")
    
    return True
