"""
Component 2 Helper: LLM Provider Abstraction (Production Mode — No Mock Data)
==============================================================================
Provides authentic interface for AI model inference supporting:
- OpenAI API (gpt-4o, gpt-4o-mini) via OPENAI_API_KEY
- Ollama local edge models (llama3.1, deepseek-r1)
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
from pydantic import BaseModel

from frontierx_brain.observability.observability import brain_logger


class LLMProviderResponse(BaseModel):
    raw_text: str
    model_used: str
    provider_name: str


class BaseLLMProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> LLMProviderResponse:
        raise NotImplementedError


class OllamaLLMProvider(BaseLLMProvider):
    """Ollama local edge model provider."""

    def __init__(self, model_name: str = "llama3.1:8b", base_url: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.base_url = base_url

    def generate(self, system_prompt: str, user_prompt: str) -> LLMProviderResponse:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return LLMProviderResponse(
                    raw_text=res_data.get("response", ""),
                    model_used=self.model_name,
                    provider_name="Ollama",
                )
        except Exception as ex:
            raise RuntimeError(f"Ollama local model request failed at {url}: {ex}")


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI API provider (gpt-4o)."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4o") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

    def generate(self, system_prompt: str, user_prompt: str) -> LLMProviderResponse:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(url, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                return LLMProviderResponse(
                    raw_text=content,
                    model_used=self.model_name,
                    provider_name="OpenAI",
                )
        except Exception as ex:
            raise RuntimeError(f"OpenAI API request failed: {ex}")


def get_llm_provider(preferred_provider: str = "auto") -> BaseLLMProvider:
    """
    Factory function returning active production LLM provider.
    No mock fallbacks. Raises RuntimeError if no valid backend is available.
    """
    if preferred_provider == "openai" or (preferred_provider == "auto" and os.getenv("OPENAI_API_KEY")):
        try:
            return OpenAILLMProvider()
        except Exception as e:
            if preferred_provider == "openai":
                raise e

    if preferred_provider in ("ollama", "auto"):
        try:
            provider = OllamaLLMProvider()
            # Test ping to check if ollama server is alive
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return provider
        except Exception:
            pass

    # If preferred_provider is explicitly requesting openai
    if os.getenv("OPENAI_API_KEY"):
        return OpenAILLMProvider()

    raise RuntimeError(
        "No active production LLM backend configured. Please set the OPENAI_API_KEY environment variable "
        "or ensure a local Ollama server is running at http://localhost:11434."
    )
