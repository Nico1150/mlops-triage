from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from mlops_triage.llm.tools import Tool, ToolExecutionError, execute_tool, tools_by_name, tools_to_openai


class AgentError(Exception):
    """Agent stopped without producing the expected result."""


def _assistant_message_dict(message: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
    }
    if message.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            }
            for tc in message.tool_calls
        ]
    return out


def run_agent(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[Tool],
    temperature: float = 0.2,
    max_steps: int = 10,
    terminal_tool: str = "submit_triage_report",
) -> BaseModel | str:
    """Run a tool loop until ``terminal_tool`` is called or the model replies without tools."""
    registry = tools_by_name(tools)
    openai_tools = tools_to_openai(tools)
    conversation = [dict(m) for m in messages]

    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=model,
            messages=conversation,
            tools=openai_tools,
            temperature=temperature,
        )
        choice = response.choices[0]
        message = choice.message
        conversation.append(_assistant_message_dict(message))

        if not message.tool_calls:
            content = (message.content or "").strip()
            if content:
                return content
            raise AgentError("Model returned an empty message without tool calls")

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            tool = registry.get(name)
            if tool is None:
                err = f"Unknown tool: {name}"
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": err}),
                    }
                )
                continue

            try:
                result = execute_tool(tool, tool_call.function.arguments or "{}")
            except ToolExecutionError as exc:
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": str(exc)}),
                    }
                )
                continue

            if name == terminal_tool:
                return tool.parameters_model.model_validate_json(result)

            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    raise AgentError(f"Agent exceeded max_steps ({max_steps}) without calling {terminal_tool}")
