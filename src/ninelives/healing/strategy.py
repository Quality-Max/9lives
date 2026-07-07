"""Healing strategy selector.

Determines which tier of healing to apply based on failure analysis. The CLI
ships Tier 1 offline locator repair, Tier 2 AI-suggested patches, and Tier 3
human handoff.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealingTier(str, Enum):
    """Healing tiers from automatic to manual."""

    TIER1_AUTO = "tier1_auto"  # Automatic locator fallbacks
    TIER2_AI_SUGGEST = "tier2_ai_suggest"  # AI suggestions, human approval
    TIER3_HUMAN = "tier3_human"  # Major changes, human required
    NO_HEALING = "no_healing"  # Cannot be healed


class FailureType(str, Enum):
    """Types of test failures."""

    LOCATOR_NOT_FOUND = "locator_not_found"
    LOCATOR_TIMEOUT = "locator_timeout"
    ELEMENT_NOT_VISIBLE = "element_not_visible"
    ELEMENT_NOT_INTERACTABLE = "element_not_interactable"
    ASSERTION_FAILED = "assertion_failed"
    NAVIGATION_FAILED = "navigation_failed"
    NETWORK_ERROR = "network_error"
    FLOW_CHANGED = "flow_changed"
    SYNTAX_ERROR = "syntax_error"
    UNKNOWN = "unknown"


@dataclass
class TestFailure:
    """Details of a test failure."""

    failure_type: FailureType
    error_message: str
    failed_selector: str | None = None
    failed_line: int | None = None
    stack_trace: str = ""
    screenshot_path: str | None = None
    console_logs: list[str] = field(default_factory=list)
    test_code: str = ""
    page_url: str = ""
    page_html: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "failed_selector": self.failed_selector,
            "failed_line": self.failed_line,
            "stack_trace": self.stack_trace,
            "screenshot_path": self.screenshot_path,
            "console_logs": self.console_logs,
            "page_url": self.page_url,
        }


@dataclass
class HealingResult:
    """Result of a healing attempt."""

    tier: HealingTier
    success: bool
    healed_code: str | None = None
    changes_made: list[str] = field(default_factory=list)
    requires_approval: bool = False
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "success": self.success,
            "changes_made": self.changes_made,
            "requires_approval": self.requires_approval,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class HealingStrategySelector:
    """Selects the appropriate healing tier based on failure analysis.

    Tier 1 (Auto): locator not found, simple selector change — offline, free.
    Tier 2 (AI-Suggest): element moved/renamed, structural change — one LLM call,
        always presented as a diff for approval.
    Tier 3 (Human): flow changed, redesign needed — analysis only.
    """

    LOCATOR_PATTERNS = [
        r"locator.*not found",
        r"element.*not found",
        r"selector.*not found",
        r"TimeoutError.*locator",
        r"waiting for selector",
        r"waiting for locator",
        r"no element matching",
        r"could not find element",
        r"strict mode violation",
    ]

    TIMEOUT_PATTERNS = [
        r"TimeoutError",
        r"Timeout.*exceeded",
        r"waiting for.*timed out",
    ]

    VISIBILITY_PATTERNS = [
        r"element.*not visible",
        r"element.*hidden",
        r"display.*none",
        r"visibility.*hidden",
        r"not interactable",
    ]

    ASSERTION_PATTERNS = [
        r"AssertionError",
        r"expect.*toBe",
        r"expect.*toHave",
        r"expected.*to be",
        r"expected.*to have",
        r"assertion failed",
    ]

    NAVIGATION_PATTERNS = [
        r"navigation.*failed",
        r"net::ERR",
        r"page.*crash",
        r"context.*closed",
        r"target.*closed",
    ]

    FLOW_CHANGE_PATTERNS = [
        r"unexpected.*page",
        r"unexpected.*url",
        r"step.*missing",
        r"element.*removed",
        r"flow.*changed",
    ]

    def classify_failure(self, error_message: str, stack_trace: str = "") -> FailureType:
        """Classify the type of failure from error message."""
        combined = f"{error_message} {stack_trace}".lower()

        for pattern in self.FLOW_CHANGE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return FailureType.FLOW_CHANGED

        for pattern in self.NAVIGATION_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return FailureType.NAVIGATION_FAILED

        for pattern in self.ASSERTION_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return FailureType.ASSERTION_FAILED

        for pattern in self.VISIBILITY_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return FailureType.ELEMENT_NOT_VISIBLE

        for pattern in self.LOCATOR_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return FailureType.LOCATOR_NOT_FOUND

        for pattern in self.TIMEOUT_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return FailureType.LOCATOR_TIMEOUT

        if "syntax" in combined or "parse" in combined:
            return FailureType.SYNTAX_ERROR

        return FailureType.UNKNOWN

    def select_strategy(self, failure: TestFailure) -> HealingTier:
        """Select the appropriate healing tier for a failure."""
        failure_type = failure.failure_type

        if failure_type in [FailureType.LOCATOR_NOT_FOUND, FailureType.LOCATOR_TIMEOUT]:
            if self._has_fallback_selectors(failure):
                return HealingTier.TIER1_AUTO
            if self._can_find_alternative(failure):
                return HealingTier.TIER1_AUTO
            return HealingTier.TIER2_AI_SUGGEST

        if failure_type == FailureType.ELEMENT_NOT_VISIBLE:
            if self._is_simple_visibility_fix(failure):
                return HealingTier.TIER1_AUTO
            return HealingTier.TIER2_AI_SUGGEST

        if failure_type == FailureType.ASSERTION_FAILED:
            if self._is_value_change(failure):
                return HealingTier.TIER2_AI_SUGGEST
            return HealingTier.TIER3_HUMAN

        if failure_type in [FailureType.NAVIGATION_FAILED, FailureType.FLOW_CHANGED]:
            return HealingTier.TIER3_HUMAN

        if failure_type == FailureType.NETWORK_ERROR:
            return HealingTier.TIER3_HUMAN

        if failure_type == FailureType.SYNTAX_ERROR:
            return HealingTier.NO_HEALING

        return HealingTier.TIER2_AI_SUGGEST

    def _has_fallback_selectors(self, failure: TestFailure) -> bool:
        """Check if fallback selectors are available."""
        if not failure.failed_selector:
            return False
        if "// fallback:" in failure.test_code.lower():
            return True
        if "data-testid" in failure.failed_selector:
            return True
        return False

    def _can_find_alternative(self, failure: TestFailure) -> bool:
        """Check if an alternative selector can be found in captured page state."""
        if not failure.page_html or not failure.failed_selector:
            return False

        selector = failure.failed_selector
        id_match = re.search(r'id=["\']([^"\']+)["\']', selector)
        text_match = re.search(r'text=["\']([^"\']+)["\']', selector)
        page_lower = failure.page_html.lower()

        if id_match and id_match.group(1).lower() in page_lower:
            return True
        if text_match and text_match.group(1).lower() in page_lower:
            return True
        return False

    def _is_simple_visibility_fix(self, failure: TestFailure) -> bool:
        """Check if visibility issue has a simple fix."""
        msg = failure.error_message.lower()
        return "scroll" in msg or "viewport" in msg

    def _is_value_change(self, failure: TestFailure) -> bool:
        """Check if assertion failure is due to value change."""
        msg = failure.error_message.lower()
        if "expected" in msg and "received" in msg:
            return True
        if "to be" in msg and "but" in msg:
            return True
        return False


healing_strategy_selector = HealingStrategySelector()
