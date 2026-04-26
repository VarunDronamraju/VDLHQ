import json
from typing import Any, Dict, List, Optional

import groq
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import LLMFailure

logger = structlog.get_logger()

# AsyncGroq reads GROQ_API_KEY from environment
_client = groq.AsyncGroq()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((groq.RateLimitError, groq.InternalServerError)),
)
async def call(
    messages: List[Dict[str, str]],
    system: str,
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 1024,
    temperature: float = 0.0,
    service_name: str = "unknown",
    lead_id: Optional[str] = None,
) -> str:
    """
    Shared Groq LLM call utility.
    Returns the assistant message content as a string.
    Raises LLMFailure after retries are exhausted.
    """
    log = logger.bind(service=service_name, lead_id=lead_id)

    try:
        response = await _client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        log.info("llm_call_success", tokens=response.usage.total_tokens)
        return content
    except (groq.RateLimitError, groq.InternalServerError) as e:
        log.warning("llm_call_retry", error=str(e))
        raise  # tenacity will retry
    except Exception as e:
        log.error("llm_call_failure", error=str(e))
        raise LLMFailure(f"Groq API error: {str(e)}")


async def call_json(
    messages: List[Dict[str, str]],
    system: str,
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 2048,
    temperature: float = 0.0,
    service_name: str = "unknown",
    lead_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calls LLM with JSON mode enabled and parses result.
    """
    log = logger.bind(service=service_name, lead_id=lead_id)

    # Inject JSON instruction if not present
    if "json" not in system.lower():
        system += "\n\nCRITICAL: You must return ONLY a valid JSON object. No preamble."

    try:
        response = await _client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, *messages],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        log.info("llm_json_call_success", tokens=response.usage.total_tokens)
        return json.loads(content)
    except json.JSONDecodeError:
        log.error("llm_json_parse_failure", content=content)
        raise LLMFailure("LLM returned invalid JSON")
    except Exception as e:
        log.error("llm_json_call_failure", error=str(e))
        raise LLMFailure(f"Groq JSON API error: {str(e)}")
