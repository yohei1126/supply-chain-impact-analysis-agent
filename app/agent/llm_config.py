from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OpenAICompatLLMSettings:
    """Settings for POST {api_base}/chat/completions (OpenAI-compatible gateways)."""

    api_base: str | None
    api_key: str | None
    model: str
    gateway: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_base and self.api_key)


def load_openai_compat_settings() -> OpenAICompatLLMSettings:
    """
    Resolve LLM endpoint from environment.

    Primary variables (OpenAI-compatible client contract):
      OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL

    Aliases for LiteLLM (or direct OpenAI):
      LLM_GATEWAY_BASE, LLM_GATEWAY_API_KEY, LLM_MODEL, LLM_GATEWAY (litellm|openai)
    """
    api_base = os.getenv("OPENAI_API_BASE") or os.getenv("LLM_GATEWAY_BASE")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_GATEWAY_API_KEY")
    model = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o-mini"
    gateway = os.getenv("LLM_GATEWAY")
    return OpenAICompatLLMSettings(
        api_base=api_base,
        api_key=api_key,
        model=model,
        gateway=gateway,
    )
