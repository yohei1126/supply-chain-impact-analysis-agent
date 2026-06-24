from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, cast

from app.agent.llm_config import OpenAICompatLLMSettings
from app.agent.telemetry import RunTracer
from app.agent.types import ToolCall


def parse_planner_response(content: str) -> dict[str, Any]:
    """Parse planner JSON; tolerate markdown fences from Gemini and similar models."""
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    return cast(dict[str, Any], json.loads(text))


def chat_completions(
    *,
    settings: OpenAICompatLLMSettings,
    messages: list[dict[str, str]],
    temperature: float = 0,
    timeout_sec: int = 120,
    tracer: RunTracer | None = None,
    generation_name: str = "chat-completion",
) -> str:
    if not settings.api_base or not settings.api_key:
        raise ValueError("LLM settings require api_base and api_key")

    payload = {
        "model": settings.model,
        "messages": messages,
        "temperature": temperature,
    }
    request = urllib.request.Request(
        f"{settings.api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    content = body["choices"][0]["message"]["content"]
    if tracer is not None:
        tracer.record_generation(
            generation_name,
            settings.model,
            messages,
            content,
        )
    return str(content)


def plan_tool_calls_openai_compat(
    goal: str,
    system_prompt: str,
    tools: list[dict[str, Any]],
    settings: OpenAICompatLLMSettings,
    tracer: RunTracer | None = None,
) -> list[ToolCall]:
    tool_summary = json.dumps(tools, ensure_ascii=False)
    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
                + "\n\nAvailable tools (JSON schema list):\n"
                + tool_summary
                + "\n\nRespond with JSON only, no markdown: "
                '{"tool_calls":[{"name":"<tool_name>","arguments":{}}]}'
            ),
        },
        {"role": "user", "content": goal},
    ]
    content = chat_completions(
        settings=settings,
        messages=messages,
        tracer=tracer,
        generation_name="planner",
    )
    try:
        parsed = parse_planner_response(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM returned non-JSON planner output: {content[:500]}") from exc

    calls: list[ToolCall] = []
    for item in parsed.get("tool_calls", []):
        calls.append(ToolCall(name=item["name"], arguments=item.get("arguments", {})))
    return calls


def summarize_run_openai_compat(
    goal: str,
    tool_calls: list[ToolCall],
    results: list[dict[str, Any]],
    settings: OpenAICompatLLMSettings,
    tracer: RunTracer | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Second LLM pass: narrative explanation grounded in tool JSON only."""
    payload = {
        "goal": goal,
        "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in tool_calls],
        "tool_results": results,
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You summarize BOM knowledge-graph tool results for manufacturing engineers.\n"
                "Rules:\n"
                "- Use ONLY facts present in tool_results JSON. Do not invent IDs or metrics.\n"
                "- Write explanation in clear English (2-5 short paragraphs).\n"
                "- evidence[] must cite specific tool output: "
                "claim, tool name, pointer (JSON path), value.\n"
                "Respond with JSON only, no markdown:\n"
                '{"explanation":"...","evidence":[{"claim":"...","tool":"...","pointer":"...","value":"..."}]}'
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    content = chat_completions(
        settings=settings,
        messages=messages,
        temperature=0.2,
        tracer=tracer,
        generation_name="summarize",
    )
    try:
        parsed = parse_planner_response(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM returned non-JSON summary: {content[:500]}") from exc

    explanation = str(parsed.get("explanation", "")).strip()
    evidence = parsed.get("evidence") or []
    if not explanation:
        raise RuntimeError("LLM summary returned empty explanation")
    if not isinstance(evidence, list):
        evidence = []
    return explanation, evidence
