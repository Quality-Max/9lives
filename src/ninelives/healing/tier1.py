"""Tier 1 locator healer — automatic selector fallbacks.

Offline and free: no LLM, no network.
"""

import logging
import re

from .strategy import HealingResult, HealingTier, TestFailure

logger = logging.getLogger(__name__)


class Tier1LocatorHealer:
    """Tier 1: automatic locator fallbacks.

    Handles: selector not found with fallback available, data-testid changes,
    simple attribute changes, visibility/scroll issues.
    """

    TRANSFORMATIONS = [
        (r"\.(\w+)-(\w+)", r'[class*="\1"]'),  # .foo-bar -> [class*="foo"]
        (r"#(\w+)", r'[id="\1"]'),  # Keep ID but different syntax
        (r'data-testid="([^"]+)"', r'[data-testid*="\1"]'),  # Partial match
    ]

    async def heal(self, failure: TestFailure) -> HealingResult:
        """Attempt to heal a locator failure automatically."""
        if not failure.failed_selector:
            return self._no_heal_result("No failed selector provided")
        if not failure.test_code:
            return self._no_heal_result("No test code provided")

        found = self._find_alternative_selector(failure)
        if found and found[0] == failure.failed_selector:
            found = None  # same selector is not a heal
        if found:
            alternative, anchor = found
            healed_code = self._replace_selector(failure.test_code, failure.failed_selector, alternative)
            return HealingResult(
                tier=HealingTier.TIER1_AUTO,
                success=True,
                healed_code=healed_code,
                changes_made=[f"Re-found via {anchor}: replaced '{failure.failed_selector}' with '{alternative}'"],
                confidence=0.85,
                metadata={"anchor": anchor, "old_selector": failure.failed_selector, "new_selector": alternative},
            )

        transformed = self._try_transformations(failure.failed_selector)
        if transformed:
            healed_code = self._replace_selector(failure.test_code, failure.failed_selector, transformed)
            return HealingResult(
                tier=HealingTier.TIER1_AUTO,
                success=True,
                healed_code=healed_code,
                changes_made=[f"Transformed selector '{failure.failed_selector}' to '{transformed}'"],
                confidence=0.7,
                metadata={"old_selector": failure.failed_selector, "new_selector": transformed},
            )

        # The wait/scroll injection writes Playwright API calls; other
        # frameworks escalate to Tier 2 instead of gaining `await page.…` lines.
        if failure.framework == "playwright" and self._is_timing_issue(failure):
            healed_code = self._add_wait_handling(failure.test_code, failure.failed_selector)
            return HealingResult(
                tier=HealingTier.TIER1_AUTO,
                success=True,
                healed_code=healed_code,
                changes_made=["Added wait/scroll handling for element"],
                confidence=0.75,
            )

        return self._no_heal_result("Could not find working alternative")

    def _find_alternative_selector(self, failure: TestFailure) -> tuple[str, str] | None:
        """Find an alternative selector in the captured page state.

        Returns (selector, anchor_type) — the anchor that re-identified the
        element — so the report can show HOW it was re-found (e.g. "re-found
        via testid"), or None when no anchor still resolves.
        """
        if not failure.page_html:
            return None
        for id_type, id_value in self._extract_identifiers(failure.failed_selector):
            alternative = self._find_in_html((id_type, id_value), failure.page_html)
            if alternative:
                return alternative, id_type
        return None

    def _extract_identifiers(self, selector: str) -> list[tuple[str, str]]:
        """Extract identifying parts from a selector."""
        identifiers = []

        # Stability order: testid > id > aria-label > text > class. We adopt the
        # first anchor that still resolves on the live page, so the most durable
        # identity wins and fragile copy/CSS churn is only the last resort.
        testid_match = re.search(r"data-testid=['\"]([^'\"]+)['\"]", selector)
        if testid_match:
            identifiers.append(("testid", testid_match.group(1)))

        id_match = re.search(r"#([a-zA-Z][\w-]*)", selector)
        if id_match:
            identifiers.append(("id", id_match.group(1)))

        aria_match = re.search(r"aria-label=['\"]([^'\"]+)['\"]", selector)
        if aria_match:
            identifiers.append(("aria-label", aria_match.group(1)))

        text_match = re.search(r"text=['\"]([^'\"]+)['\"]", selector)
        if text_match:
            identifiers.append(("text", text_match.group(1)))

        for cls in re.findall(r"\.([a-zA-Z][\w-]*)", selector):
            identifiers.append(("class", cls))

        return identifiers

    def _find_in_html(self, identifier: tuple[str, str], html: str) -> str | None:
        """Find an element in HTML by identifier."""
        id_type, id_value = identifier

        if id_type == "text":
            # Return the text as it actually appears on the page — copy tweaks
            # like "Sign In" -> "Sign in" are healed by adopting the live casing.
            match = re.search(re.escape(id_value), html, re.IGNORECASE)
            if match:
                return f"text='{match.group(0)}'"

        elif id_type == "testid":
            pattern = rf'data-testid=["\']([^"\']*{re.escape(id_value)}[^"\']*)["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return f"[data-testid='{match.group(1)}']"

        elif id_type == "id":
            pattern = rf'id=["\']([^"\']*{re.escape(id_value)}[^"\']*)["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return f"#{match.group(1)}"

        elif id_type == "class":
            pattern = rf'class=["\'][^"\']*({re.escape(id_value)})[^"\']*["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return f".{match.group(1)}"

        elif id_type == "aria-label":
            if id_value.lower() in html.lower():
                return f"[aria-label='{id_value}']"

        return None

    def _try_transformations(self, selector: str) -> str | None:
        """Try transforming the selector using known patterns."""
        for pattern, replacement in self.TRANSFORMATIONS:
            if re.search(pattern, selector):
                return re.sub(pattern, replacement, selector)
        return None

    def _is_timing_issue(self, failure: TestFailure) -> bool:
        msg_lower = failure.error_message.lower()
        return any(kw in msg_lower for kw in ["timeout", "waiting", "not visible", "viewport"])

    def _add_wait_handling(self, code: str, selector: str) -> str:
        """Add wait/scroll handling before problematic selector."""
        lines = code.split("\n")
        new_lines = []
        for line in lines:
            if selector in line and "locator" in line.lower():
                indent = len(line) - len(line.lstrip())
                wait_line = " " * indent + f"await page.locator('{selector}').waitFor({{ state: 'visible', timeout: 10000 }});"
                new_lines.append(wait_line)
            new_lines.append(line)
        return "\n".join(new_lines)

    def _replace_selector(self, code: str, old_selector: str, new_selector: str) -> str:
        # Function replacement (not a template string) so backslashes or group
        # references like \1 in the new selector — e.g. a page showing a Windows
        # path — are inserted literally instead of raising re.error.
        return re.sub(re.escape(old_selector), lambda _m: new_selector, code)

    def _no_heal_result(self, reason: str) -> HealingResult:
        return HealingResult(tier=HealingTier.TIER1_AUTO, success=False, metadata={"reason": reason})

    def generate_fallback_selectors(self, selector: str) -> list[str]:
        """Generate fallback selectors for a given selector (proactive use)."""
        fallbacks = []
        for id_type, id_value in self._extract_identifiers(selector):
            if id_type == "text":
                fallbacks.append(f"text='{id_value}'")
                fallbacks.append(f"text=/{id_value}/i")
            elif id_type == "testid":
                fallbacks.append(f"[data-testid='{id_value}']")
                fallbacks.append(f"[data-testid*='{id_value}']")
            elif id_type == "id":
                fallbacks.append(f"#{id_value}")
                fallbacks.append(f"[id='{id_value}']")
            elif id_type == "class":
                fallbacks.append(f".{id_value}")
                fallbacks.append(f"[class*='{id_value}']")
            elif id_type == "aria-label":
                fallbacks.append(f"[aria-label='{id_value}']")
                fallbacks.append(f"role=button >> text='{id_value}'")
        return list(set(fallbacks))[:5]


tier1_healer = Tier1LocatorHealer()
