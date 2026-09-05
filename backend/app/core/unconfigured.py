"""Null objects for capabilities whose credentials are missing.

The rule this file exists to enforce: **a missing key must fail loudly, not quietly
pretend.** Substituting a simulator for a real integration produces the worst possible
failure mode, work that reports success and has no effect on the world. Creating a voice
agent against an in-memory fake looks identical to creating a real one, right down to the
returned id, until you restart the process and it is gone.

So when a credential is absent, the capability is replaced by one of these. Every method
raises `FeatureDisabled`, which the error handler renders as a 503 carrying a stable code
the UI can switch on and a message that names the environment variable to set.

The simulators still exist and are still useful; `tests/` injects them directly. They are
just no longer reachable by forgetting to configure something.
"""

from __future__ import annotations

from typing import Any, NoReturn

from app.core.errors import FeatureDisabled


class MissingCredential(FeatureDisabled):
    code = "credential_missing"


def _refuse(capability: str, env_var: str, consequence: str) -> NoReturn:
    raise MissingCredential(
        f"{capability} is not configured. Set {env_var} in the backend environment. {consequence}",
        details={"capability": capability, "envVar": env_var},
    )


class UnconfiguredHunarClient:
    """Stands in for the voice platform when HUNAR_API_KEY is absent."""

    configured = False

    @staticmethod
    def _no() -> NoReturn:
        _refuse(
            "The Hunar voice platform",
            "HUNAR_API_KEY",
            "Agents and calls are refused rather than simulated, so nothing looks like it worked.",
        )

    async def list_agents(self, **_: Any) -> NoReturn:
        self._no()

    async def get_agent(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def create_agent(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def update_agent(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def create_call(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def create_calls_bulk(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def get_call(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def list_calls(self, **_: Any) -> NoReturn:
        self._no()

    async def list_numbers(self) -> NoReturn:
        self._no()

    async def aclose(self) -> None:
        return None


class UnconfiguredLlm:
    """Stands in for the language model when OPENROUTER_API_KEY is absent.

    Set ALLOW_DEGRADED_LLM=true to opt into the rule-based parser instead. That is a
    deliberate choice for offline work, not something you should get by accident: its
    output looks like model output and is not.
    """

    enabled = False
    configured = False

    @staticmethod
    def _no() -> NoReturn:
        _refuse(
            "The language model",
            "OPENROUTER_API_KEY",
            "Set ALLOW_DEGRADED_LLM=true to fall back to the offline rule-based parser instead.",
        )

    async def parse_job(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def draft_agent(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def assess_call(self, *_: Any, **__: Any) -> NoReturn:
        self._no()

    async def transcribe(self, *_: Any, **__: Any) -> NoReturn:
        self._no()
