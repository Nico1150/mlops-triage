from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters_model: type[BaseModel]
    handler: Callable[[BaseModel], Any]

    def to_openai(self) -> dict[str, Any]:
        schema = self.parameters_model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


def tools_to_openai(tools: list[Tool]) -> list[dict[str, Any]]:
    return [t.to_openai() for t in tools]


def tools_by_name(tools: list[Tool]) -> dict[str, Tool]:
    return {t.name: t for t in tools}


class ToolExecutionError(Exception):
    """Invalid tool arguments or unknown tool."""


def execute_tool(tool: Tool, arguments_json: str) -> str:
    try:
        payload = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as exc:
        raise ToolExecutionError(f"Tool arguments are not valid JSON: {exc}") from exc

    try:
        args = tool.parameters_model.model_validate(payload)
    except ValidationError as exc:
        raise ToolExecutionError(f"Tool argument validation failed: {exc}") from exc

    result = tool.handler(args)
    if isinstance(result, BaseModel):
        return result.model_dump_json()
    if isinstance(result, str):
        return result
    return json.dumps(result, default=str)
