"""BYO-everything LLM client: subscription CLIs first, API keys second.

Provider resolution order:
1. NINELIVES_PROVIDER env var (claude-code | codex | opencode | anthropic | openai)
2. An installed coding-agent CLI — the subscription the user already pays for
3. An API key in the environment (ANTHROPIC_API_KEY, then OPENAI_API_KEY)

SDKs are imported lazily so Tier 1 (offline) healing works with nothing
installed, and subscription mode works with no Python SDK at all.
"""

import logging
import os

from .agent_cli import AGENT_COMMANDS, call_agent_cli, detect_agent_clis

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
}

_KEY_ENVS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class LLMError(RuntimeError):
    """Raised when no provider is configured or a provider call fails."""


class LLMClient:
    """Synchronous BYO client for the healing loop's single Tier-2 call."""

    def __init__(self, provider: str | None = None, model: str | None = None, api_key: str | None = None):
        self.provider = provider or os.environ.get("NINELIVES_PROVIDER") or self._detect_provider()
        self.model = model or os.environ.get("NINELIVES_MODEL") or DEFAULT_MODELS.get(self.provider or "", "")
        self._api_key = api_key

    @staticmethod
    def _detect_provider() -> str | None:
        # Subscription CLIs win: they're already paid for and already logged in.
        clis = detect_agent_clis()
        if clis:
            return clis[0]
        return LLMClient._api_key_provider()

    @staticmethod
    def _api_key_provider() -> str | None:
        for provider, env in _KEY_ENVS.items():
            if os.environ.get(env):
                return provider
        return None

    @property
    def is_subscription(self) -> bool:
        return self.provider in AGENT_COMMANDS

    @property
    def available(self) -> bool:
        if self.provider is None:
            return False
        if self.is_subscription:
            # The CLI being on PATH doesn't prove it's logged in, but an API key
            # in the environment is a usable fallback the call path will take.
            return self.provider in detect_agent_clis() or bool(self._api_key_provider())
        return bool(self._api_key or os.environ.get(_KEY_ENVS.get(self.provider, "")))

    def call(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """Send one prompt to the configured provider and return the text reply."""
        if not self.available:
            raise LLMError(
                "No LLM provider found. Install/log in to a coding-agent CLI (claude, codex, opencode) "
                "or set ANTHROPIC_API_KEY / OPENAI_API_KEY. Tier 1 offline healing works without either."
            )

        if self.is_subscription:
            try:
                return call_agent_cli(self.provider, system, user)
            except RuntimeError as e:
                # A CLI on PATH but not logged in shouldn't dead-end when the
                # user also has an API key configured — fall back to it.
                fallback = self._api_key_provider()
                if not fallback:
                    raise LLMError(f"{self.provider} subscription call failed: {e}") from e
                logger.warning("%s subscription call failed (%s); falling back to %s API key", self.provider, e, fallback)
                self.provider = fallback
                if not self.model:
                    self.model = DEFAULT_MODELS.get(fallback, "")
        if self.provider == "anthropic":
            return self._call_anthropic(system, user, max_tokens, temperature)
        if self.provider == "openai":
            return self._call_openai(system, user, max_tokens, temperature)
        raise LLMError(f"Unknown provider: {self.provider}")

    def _call_anthropic(self, system: str, user: str, max_tokens: int, temperature: float) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("anthropic SDK not installed — pip install '9lives[anthropic]'") from e

        try:
            client = anthropic.Anthropic(api_key=self._api_key) if self._api_key else anthropic.Anthropic()
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        except Exception as e:
            raise LLMError(f"Anthropic call failed: {e}") from e

    def _call_openai(self, system: str, user: str, max_tokens: int, temperature: float) -> str:
        try:
            import openai
        except ImportError as e:
            raise LLMError("openai SDK not installed — pip install '9lives[openai]'") from e

        try:
            client = openai.OpenAI(api_key=self._api_key) if self._api_key else openai.OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"OpenAI call failed: {e}") from e
