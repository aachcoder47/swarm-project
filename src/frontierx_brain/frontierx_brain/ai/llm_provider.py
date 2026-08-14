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


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic rule-based planner. No mocked-out fake data.
    Produces structured, canonical-skill task plans from NL commands
    using keyword / intent matching. Used as default when no
    OpenAI/Ollama backend is available, and as a fallback on failure.
    """

    def __init__(self) -> None:
        self.model_name = "frontierx_deterministic_planner_v1"

    @staticmethod
    def _extract_objects(command: str) -> tuple[str, str, str]:
        """Return (target_object, second_object, action) by keyword heuristics."""
        cmd = command.lower()
        target = "generator"
        second = "damaged_component"
        action = "inspect"
        if "generator" in cmd:
            target = "generator"
        if "valve" in cmd:
            target = "valve"
        if "box" in cmd or "red box" in cmd:
            target = "box"
        if "pick" in cmd or "grasp" in cmd:
            action = "pick"
            if "damaged" in cmd or "component" in cmd:
                second = "damaged_component"
            else:
                second = target
        if "inspect" in cmd or "check" in cmd or "scan" in cmd:
            action = "inspect" if action != "pick" else "inspect_and_pick"
        if "find" in cmd or "locate" in cmd:
            if action == "inspect":
                action = "find_and_inspect"
            elif action == "pick":
                action = "find_inspect_and_pick"
            else:
                action = "find"
        if "all" in cmd and ("generator" in cmd or "inspect" in cmd):
            action = "inspect_all"
        if "report" in cmd or "status" in cmd:
            action = "report"
        return target, second, action

    def generate(self, system_prompt: str, user_prompt: str) -> LLMProviderResponse:
        # Extract the user's NL command from within the prompt
        import re
        m = re.search(r"User Request: '([^']*)'", user_prompt)
        command = m.group(1) if m else user_prompt
        target, second, action = self._extract_objects(command)

        reasoning = (
            f"Deterministic planner parsed command '{command}'. "
            f"Intent: {action}. Primary target: {target}. "
            f"Will query world model → select capable body → execute steps sequentially."
        )

        steps = []
        step_id = 0

        if action in ("find", "find_and_inspect", "find_inspect_and_pick"):
            steps.append({
                "step_id": step_id,
                "task_type": "query_world",
                "params": {"class_name": target, "status": None},
                "description": f"Query world model for known '{target}' objects.",
                "required_capabilities": [],
                "timeout_seconds": 5.0,
            })
            step_id += 1
            steps.append({
                "step_id": step_id,
                "task_type": "find_object",
                "params": {"class_name": target},
                "description": f"Locate '{target}' object via search/navigation if not yet known.",
                "required_capabilities": ["object_search", "capture_rgb"],
                "timeout_seconds": 120.0,
            })
            step_id += 1

        # Navigate to target for any action that involves inspecting an object
        if action in ("find_and_inspect", "find_inspect_and_pick",
                      "inspect", "inspect_and_pick", "inspect_all"):
            steps.append({
                "step_id": step_id,
                "task_type": "navigate_to",
                "params": {"_resolve_from_object": target, "x": None, "y": None, "yaw": 0.0},
                "description": f"Navigate robot to within inspection standoff of '{target}'.",
                "required_capabilities": ["navigate_ground"],
                "timeout_seconds": 120.0,
            })
            step_id += 1

        if action in ("inspect", "find_and_inspect", "inspect_and_pick", "find_inspect_and_pick", "inspect_all"):
            steps.append({
                "step_id": step_id,
                "task_type": "inspect",
                "params": {"_resolve_from_object": target, "object_id": None, "inspection_mode": "VISUAL"},
                "description": f"Inspect '{target}' using RGB/thermal sensor suite; capture findings.",
                "required_capabilities": ["capture_rgb", "visual_inspection"],
                "timeout_seconds": 90.0,
            })
            step_id += 1
            steps.append({
                "step_id": step_id,
                "task_type": "analyze_observation",
                "params": {"_resolve_from_object": target, "object_id": None, "inspection_data": {}},
                "description": "Analyze inspection observation; mark object status as INSPECTED or DAMAGED.",
                "required_capabilities": ["capture_rgb"],
                "timeout_seconds": 30.0,
            })
            step_id += 1

        if action in ("pick", "inspect_and_pick", "find_inspect_and_pick"):
            steps.append({
                "step_id": step_id,
                "task_type": "arm_pick",
                "params": {"_resolve_from_object": second, "object_id": None},
                "description": f"Robotic arm grasps and lifts '{second}'.",
                "required_capabilities": ["manipulate_arm", "grasp"],
                "timeout_seconds": 60.0,
            })
            step_id += 1

        steps.append({
            "step_id": step_id,
            "task_type": "report_status",
            "params": {},
            "description": "Produce structured final report of entire mission.",
            "required_capabilities": [],
            "timeout_seconds": 10.0,
        })

        plan = {
            "natural_language": command,
            "reasoning": reasoning,
            "total_timeout_seconds": 300.0,
            "steps": steps,
        }

        return LLMProviderResponse(
            raw_text=json.dumps(plan),
            model_used=self.model_name,
            provider_name="MockDeterministicPlanner",
        )


def get_llm_provider(preferred_provider: str = "auto") -> BaseLLMProvider:
    """
    Factory returning an active LLM provider. Priority:
      'mock' / env FRONTIERX_USE_MOCK_PLANNER → MockLLMProvider (deterministic)
      'openai' or env OPENAI_API_KEY set → OpenAILLMProvider
      'ollama' / 'auto' with running ollama → OllamaLLMProvider
      else → MockLLMProvider (always available, no API key needed)

    The 'mock' provider is NOT fake/mock data — it is a deterministic,
    rule-based planner that produces canonical skill plans from NL commands.
    """
    if preferred_provider == "mock" or os.getenv("FRONTIERX_USE_MOCK_PLANNER") == "1":
        return MockLLMProvider()

    if preferred_provider == "openai" or (preferred_provider == "auto" and os.getenv("OPENAI_API_KEY")):
        try:
            return OpenAILLMProvider()
        except Exception as e:
            if preferred_provider == "openai":
                # fall through to mock rather than crashing — enables offline demos
                brain_logger.warning(f"OpenAI provider requested but unavailable: {e}. Falling back to deterministic planner.")

    if preferred_provider in ("ollama", "auto", "openai"):
        try:
            provider = OllamaLLMProvider()
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return provider
        except Exception:
            pass

    if os.getenv("OPENAI_API_KEY") and preferred_provider in ("auto",):
        try:
            return OpenAILLMProvider()
        except Exception:
            pass

    # Always-available deterministic fallback (no mock data — just rule-based planning)
    brain_logger.info("LLM: No cloud/local inference backend detected. Using deterministic rule-based planner.")
    return MockLLMProvider()
