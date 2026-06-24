"""
Base class for all CareerPilot agents.
Provides common LLM access, structured logging into AgentRun table,
and a consistent `run(state) -> partial_state_update` interface
expected by LangGraph nodes.

FIX: LLM is now lazy-loaded on first use (_llm = None), NOT at
__init__ time. This means the .env file is fully loaded before
the LLM client is ever constructed, avoiding the
DefaultCredentialsError that occurs when google-genai tries to
fall back to ADC because the API key isn't available yet at
module import time.
"""
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, Any
from backend.db.session import SessionLocal
from backend.db.models import AgentRun


class BaseAgent(ABC):
    name: str = "base_agent"

    def __init__(self, temperature: float = 0.3):
        self._temperature = temperature
        self._llm = None          # lazy — built on first use

    @property
    def llm(self):
        """Lazy LLM property: constructed only on first access,
        after .env has been loaded by pydantic-settings."""
        if self._llm is None:
            from backend.core.llm import get_llm
            self._llm = get_llm(temperature=self._temperature)
        return self._llm

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's logic and return a partial state update."""
        raise NotImplementedError

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node entrypoint - wraps run() with logging/timing."""
        start = time.time()
        status = "success"
        try:
            result = self.run(state)
        except Exception as exc:  # noqa: BLE001
            status = "error"
            result = {"logs": [f"[{self.name}] ERROR: {exc}"]}
        duration_ms = int((time.time() - start) * 1000)
        self._log_run(state, result, status, duration_ms)
        return result

    def _log_run(self, state, result, status, duration_ms):
        db = SessionLocal()
        try:
            run = AgentRun(
                agent_name=self.name,
                input_summary=json.dumps({"task": state.get("task", "")})[:1000],
                output_summary=json.dumps(
                    {k: v for k, v in result.items() if k not in ("messages", "logs")},
                    default=str
                )[:2000],
                status=status,
                duration_ms=duration_ms,
            )
            db.add(run)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def invoke_llm(self, prompt: str) -> str:
        """Convenience wrapper for a single-turn LLM call."""
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
