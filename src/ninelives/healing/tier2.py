"""Tier 2 AI suggest — LLM-suggested fixes, always shown as a diff for approval."""

import logging
import re
from typing import ClassVar

from ..llm.client import LLMClient, LLMError
from .patch import comments_changed
from .strategy import HealingResult, HealingTier, TestFailure

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert test automation engineer. Analyze test failures and suggest minimal fixes. "
    "Change only what the failure requires; never edit comments, imports, or unrelated tests, and never "
    "claim a change was tested or verified — verification happens by re-running the test, not by you."
)


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

        if comments_changed(failure.test_code, healed_code):
            # Enforce the prompt's comment boundary. A legitimate code fix must
            # not smuggle fabricated "verified" prose into the user's file.
            return HealingResult(
                tier=HealingTier.TIER2_AI_SUGGEST,
                success=False,
                requires_approval=True,
                metadata={
                    "reason": "AI suggestion edited comments or surrounding whitespace",
                    "ai_reasoning": suggestion,
                    "original_error": failure.error_message,
                },
            )

        return HealingResult(
            tier=HealingTier.TIER2_AI_SUGGEST,
            success=healed_code != failure.test_code,
            healed_code=healed_code,
            changes_made=changes,
            requires_approval=True,  # Always requires approval
            confidence=0.7,
            metadata={"ai_reasoning": suggestion, "original_error": failure.error_message},
        )

    # Framework → (human label, code-fence language) for the prompt.
    FRAMEWORK_LABELS: ClassVar[dict[str, tuple[str, str]]] = {
        "playwright": ("Playwright", "javascript"),
        "cypress": ("Cypress", "javascript"),
        "selenium": ("Selenium (Python + pytest)", "python"),
    }

    def _build_prompt(self, failure: TestFailure) -> str:
        """Build prompt for AI suggestion."""
        label, fence = self.FRAMEWORK_LABELS.get(failure.framework, ("Playwright", "javascript"))
        lines = [
            f"A {label} test is failing. Please suggest a fix.",
            "",
            "## Error Details",
            f"Error Type: {failure.failure_type.value}",
            f"Error Message: {failure.error_message}",
            "",
        ]

        if failure.failed_selector:
            lines.extend([f"Failed Selector: {failure.failed_selector}", ""])

        lines.extend(["## Test Code", f"```{fence}", failure.test_code, "```", ""])

        if failure.page_html:
            lines.extend(["## Page state at failure (snippet)", "```", failure.page_html[:3000], "```", ""])

        if failure.console_logs:
            lines.extend(["## Console Logs", "\n".join(failure.console_logs[:10]), ""])

        lines.extend(
            [
                "## Instructions",
                "1. Analyze why the test is failing",
                "2. Suggest a minimal fix: change only the line(s) that cause THIS failure",
                "3. Do not edit comments, imports, or other tests; do not reformat or add advice",
                "4. Do not describe anything as tested or verified — 9lives re-runs the test to verify",
                "5. Provide the corrected code (the COMPLETE test file)",
                "6. Explain the changes made",
                "",
                "## Output Format",
                "REASONING: <your analysis>",
                "CHANGES: <list of changes>",
                "CODE:",
                f"```{fence}",
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
        code_match = re.search(
            r"CODE:\s*```(?:javascript|typescript|python|js|ts|py)?\s*\n(.*?)```", suggestion, re.DOTALL | re.IGNORECASE
        )
        if code_match:
            return self._match_trailing_newline(code_match.group(1).strip(), original_code)

        code_block = re.search(r"```(?:javascript|typescript|python|js|ts|py)?\s*\n(.*?)```", suggestion, re.DOTALL)
        if code_block:
            return self._match_trailing_newline(code_block.group(1).strip(), original_code)

        return original_code

    @staticmethod
    def _match_trailing_newline(code: str, original_code: str) -> str:
        """Keep the file's trailing-newline convention so the diff shows only the fix."""
        if original_code.endswith("\n") and not code.endswith("\n"):
            return code + "\n"
        return code

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
