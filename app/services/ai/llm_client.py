import json
import os
import sys
from typing import Any, Dict, List, Optional

import groq
import httpx
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


async def _call_ollama(
    messages: List[Dict[str, str]],
    system: str,
    max_tokens: int,
    temperature: float,
    response_format_json: bool = False,
) -> str:
    """
    Calls local Ollama service as a fallback.
    """
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    formatted_messages = [{"role": "system", "content": system}] + messages

    payload = {
        "model": ollama_model,
        "messages": formatted_messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    if response_format_json:
        payload["format"] = "json"

    url = f"{ollama_base.rstrip('/')}/api/chat"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        res_json = response.json()
        return res_json["message"]["content"]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((groq.RateLimitError, groq.InternalServerError)),
)
async def _call_groq(
    messages: List[Dict[str, str]],
    system: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> tuple[str, int]:
    """
    Internal Groq LLM call utility.
    """
    response = await _client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content, response.usage.total_tokens


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
    Shared LLM call utility with Ollama fallback.
    Returns the assistant message content as a string.
    Raises LLMFailure after retries and fallback are exhausted.
    """
    log = logger.bind(service=service_name, lead_id=lead_id)

    try:
        content, total_tokens = await _call_groq(
            messages=messages,
            system=system,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        log.info("llm_call_success", tokens=total_tokens)
        return content
    except Exception as e:
        log.warning("llm_groq_failure_triggering_fallback", error=str(e))
        ollama_base = os.getenv("OLLAMA_BASE_URL")
        if ollama_base and ("pytest" not in sys.modules or os.getenv("TEST_OLLAMA_FALLBACK") == "true"):
            try:
                log.info("llm_fallback_ollama_started", base_url=ollama_base)
                content = await _call_ollama(
                    messages=messages,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format_json=False,
                )
                log.info("llm_fallback_ollama_success")
                return content
            except Exception as ollama_err:
                log.error("llm_fallback_ollama_failure", error=str(ollama_err))
                raise LLMFailure(f"Groq failed: {str(e)}. Ollama fallback also failed: {str(ollama_err)}")
        else:
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
    Calls LLM with JSON mode enabled and parses result, with Ollama fallback.
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
    except Exception as e:
        log.warning("llm_json_groq_failure_triggering_fallback", error=str(e))
        ollama_base = os.getenv("OLLAMA_BASE_URL")
        if ollama_base and ("pytest" not in sys.modules or os.getenv("TEST_OLLAMA_FALLBACK") == "true"):
            try:
                log.info("llm_json_fallback_ollama_started", base_url=ollama_base)
                content = await _call_ollama(
                    messages=messages,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format_json=True,
                )
                log.info("llm_json_fallback_ollama_success")
                return json.loads(content)
            except json.JSONDecodeError as json_err:
                log.error("llm_json_fallback_ollama_parse_failure", content=content)
                raise LLMFailure(f"Ollama JSON decode error: {str(json_err)}")
            except Exception as ollama_err:
                log.error("llm_json_fallback_ollama_failure", error=str(ollama_err))
                raise LLMFailure(f"Groq JSON failed: {str(e)}. Ollama JSON fallback also failed: {str(ollama_err)}")
        else:
            if isinstance(e, json.JSONDecodeError):
                log.error("llm_json_parse_failure", content=locals().get("content", ""))
                raise LLMFailure("LLM returned invalid JSON")
            log.error("llm_json_call_failure", error=str(e))
            raise LLMFailure(f"Groq JSON API error: {str(e)}")
