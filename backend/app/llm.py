import json
import re
from typing import Any

import httpx

from app.config import settings


class LLMConfigurationError(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


def chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    if not settings.groq_api_key:
        raise LLMConfigurationError(
            "Groq is not configured. Add GROQ_API_KEY to backend/.env and restart FastAPI."
        )

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=90,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str):
            raise ValueError("Model response did not contain text")
        content = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content, flags=re.IGNORECASE)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Model response was not a JSON object")
        return parsed
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise LLMProviderError(
            "Groq could not return a usable response. Check the API key, model access, free-tier limits, and try again."
        ) from exc
