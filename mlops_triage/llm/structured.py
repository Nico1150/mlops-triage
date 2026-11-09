from __future__ import annotations

import json
import re
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class StructuredOutputError(Exception):
    """Raised when structured output cannot be parsed or validated after retries."""


def _schema_system_prompt(response_model: type[BaseModel]) -> str:
    schema = json.dumps(response_model.model_json_schema(), indent=2)
    return (
        "You extract structured data. Respond with a single JSON object that "
        "matches the JSON Schema below. No markdown, no prose outside JSON.\n\n"
        f"{schema}"
    )


def _merge_system_message(messages: list[dict[str, str]], system_content: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    system_found = False
    for msg in messages:
        if msg.get("role") == "system" and not system_found:
            combined = f"{msg['content'].rstrip()}\n\n{system_content}"
            out.append({"role": "system", "content": combined})
            system_found = True
        else:
            out.append(dict(msg))
    if not system_found:
        out.insert(0, {"role": "system", "content": system_content})
    return out


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def parse_structured_response(raw: str, response_model: type[T]) -> T:
    """Parse and validate raw model text (tests and custom callers)."""
    return _parse_and_validate(raw, response_model)


def _parse_and_validate(raw: str, response_model: type[T]) -> T:
    payload = _strip_json_fences(raw)
    try:
        return response_model.model_validate_json(payload)
    except ValidationError:
        data = json.loads(payload)
        return response_model.model_validate(data)


def complete_structured(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    response_model: type[T],
    temperature: float = 0.2,
    max_retries: int = 2,
) -> T:
    """
    Chat completion that returns a validated Pydantic model.

    Uses OpenAI-style json_object when supported; retries on validation errors.
    """
    system_content = _schema_system_prompt(response_model)
    conversation = _merge_system_message(messages, system_content)
    last_error: str | None = None
    last_raw: str | None = None

    attempts = max_retries + 1
    for attempt in range(attempts):
        if last_error and last_raw:
            conversation = conversation + [
                {"role": "assistant", "content": last_raw},
                {
                    "role": "user",
                    "content": (
                        "The previous JSON failed validation. Fix it and reply with "
                        "only valid JSON matching the schema. Error:\n"
                        f"{last_error}"
                    ),
                },
            ]

        response = client.chat.completions.create(
            model=model,
            messages=conversation,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            last_error = "Empty model response"
            last_raw = ""
            continue

        try:
            return _parse_and_validate(content, response_model)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            last_raw = content
            if attempt == attempts - 1:
                raise StructuredOutputError(
                    f"Failed to produce valid {response_model.__name__} after "
                    f"{attempts} attempt(s): {last_error}"
                ) from exc

    raise StructuredOutputError("Structured completion failed unexpectedly")
