import json

import pytest

from bom_graph.agent.llm_client import parse_planner_response
from bom_graph.agent.llm_config import OpenAICompatLLMSettings, load_openai_compat_settings


def test_parse_planner_response_plain_json():
    raw = '{"tool_calls":[{"name":"bom_supplier_impact","arguments":{"supplier_id":"SUP-001"}}]}'
    parsed = parse_planner_response(raw)
    assert parsed["tool_calls"][0]["name"] == "bom_supplier_impact"


def test_parse_planner_response_markdown_fence():
    raw = """Here is the plan:
```json
{"tool_calls":[{"name":"bom_supply_path","arguments":{"from_component_id":"COMP-100","to_product_id":"PROD-900"}}]}
```
"""
    parsed = parse_planner_response(raw)
    assert parsed["tool_calls"][0]["name"] == "bom_supply_path"


def test_openai_compat_settings_aliases(monkeypatch):
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_GATEWAY_BASE", "http://127.0.0.1:4000/v1")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "bom-gemini-planner")
    monkeypatch.setenv("LLM_GATEWAY", "litellm")

    settings = load_openai_compat_settings()
    assert settings.api_base == "http://127.0.0.1:4000/v1"
    assert settings.api_key == "test-key"
    assert settings.model == "bom-gemini-planner"
    assert settings.gateway == "litellm"
    assert settings.configured


def test_openai_compat_settings_not_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_BASE", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)

    settings = OpenAICompatLLMSettings(api_base=None, api_key=None, model="x")
    assert not settings.configured
