"""Tier 2 AI suggest — LLM-suggested fixes, always shown as a diff for approval."""

import logging
import re

from ..llm.client import LLMClient, LLMError
from .strategy import HealingResult, HealingTier, TestFailure

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are an expert test automation engineer. Analyze test failures and suggest minimal fixes."


class Tier2AISuggest:
    """Tier 2: AI-suggested fixes with human approval.

    Handles: element moved/renamed, structural changes, assertion value
    changes, multiple selector failures.
    """

    def __init__(self, client: LLMClient | None = None):
        self._client = client or LLMClient()

    async def suggest(self, failure: TestFailure) -> HealingResult:
        """Generate an AI-suggested fix for the failure."""
        prompt = self._build_prompt(failure)
        suggestion = self._get_ai_suggestion(prompt)

        if not suggestion:
            return HealingResult(
                tier=HealingTier.TIER2_AI_SUGGEST,
                success=False,
                requires_approval=True,
                metadata={"reason": "AI suggestion failed"},
            )

        healed_code = self._parse_suggestion(suggestion, failure.test_code)
        changes = self._extract_changes(suggestion)

        return HealingResult(
            tier=HealingTier.TIER2_AI_SUGGEST,
            success=healed_code != failure.test_code,
            healed_code=healed_code,
            changes_made=changes,
            requires_approval=True,  # Always requires approval
            confidence=0.7,
            metadata={"ai_reasoning": suggestion, "original_error": failure.error_message},
        )

    def _build_prompt(self, failure: TestFailure) -> str:
        """Build prompt for AI suggestion."""
        lines = [
            "A Playwright test is failing. Please suggest a fix.",
            "",
            "## Error Details",
            f"Error Type: {failure.failure_type.value}",
            f"Error Message: {failure.error_message}",
            "",
        ]

        if failure.failed_selector:
            lines.extend([f"Failed Selector: {failure.failed_selector}", ""])

        lines.extend(["## Test Code", "```javascript", failure.test_code, "```", ""])

        if failure.page_html:
            lines.extend(["## Page state at failure (snippet)", "```", failure.page_html[:3000], "```", ""])

        if failure.console_logs:
            lines.extend(["## Console Logs", "\n".join(failure.console_logs[:10]), ""])

        lines.extend(
            [
                "## Instructions",
                "1. Analyze why the test is failing",
                "2. Suggest a minimal fix",
                "3. Provide the corrected code (the COMPLETE test file)",
                "4. Explain the changes made",
                "",
                "## Output Format",
                "REASONING: <your analysis>",
                "CHANGES: <list of changes>",
                "CODE:",
                "```javascript",
                "<corrected code>",
                "```",
            ]
        )
        return "\n".join(lines)

    def _get_ai_suggestion(self, prompt: str) -> str | None:
        """Get suggestion from the user's own LLM provider."""
        try:
            return self._client.call(system=SYSTEM_PROMPT, user=prompt, max_tokens=2000, temperature=0.2)
        except LLMError as e:
            logger.error("AI suggestion failed: %s", e)
            return None

    def _parse_suggestion(self, suggestion: str, original_code: str) -> str:
        """Parse the healed code from AI suggestion."""
        code_match = re.search(r"CODE:\s*```(?:javascript|typescript)?\s*\n(.*?)```", suggestion, re.DOTALL | re.IGNORECASE)
        if code_match:
            return code_match.group(1).strip()

        code_block = re.search(r"```(?:javascript|typescript)?\s*\n(.*?)```", suggestion, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        return original_code

    def _extract_changes(self, suggestion: str) -> list[str]:
        """Extract list of changes from AI suggestion."""
        changes = []
        changes_match = re.search(r"CHANGES:\s*(.*?)(?:CODE:|$)", suggestion, re.DOTALL | re.IGNORECASE)
        if changes_match:
            for line in changes_match.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                    changes.append(re.sub(r"^[-*•\d.]+\s*", "", line))
        if not changes:
            changes = ["AI suggested code modifications"]
        return changes[:5]
