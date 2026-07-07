"""Failure-output parsing helpers.

Includes selector extraction from Playwright output and fenced-code extraction
from LLM responses.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Playwright locator call patterns that carry a selector argument. The
# backreference (\1) matches the closing quote of the same type, and \\. lets
# escaped quotes pass through — Playwright call logs print nested quotes as
# locator('text=\'Sign In\'').
_QUOTED = r"(['\"])((?:\\.|(?!\1).)*)\1"
_SELECTOR_CALL = re.compile(
    r"(?:locator|page\.locator|getByRole|getByText|getByTestId|getByLabel|getByPlaceholder|getByTitle)"
    r"\(" + _QUOTED,
    re.IGNORECASE,
)
_WAITING_FOR = re.compile(r"waiting for (?:locator|selector)\s*\(?" + _QUOTED + r"\)?", re.IGNORECASE)


def _unescape(selector: str) -> str:
    return selector.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")


def extract_failed_selector(error_message: str, stack_trace: str = "") -> str | None:
    """Extract the failing selector from a Playwright error message."""
    combined = f"{error_message}\n{stack_trace}"

    match = _WAITING_FOR.search(combined)
    if match:
        return _unescape(match.group(2))

    match = _SELECTOR_CALL.search(combined)
    if match:
        return _unescape(match.group(2))

    return None


def extract_code_from_response(response: str, framework: str = "javascript") -> str | None:
    """Extract a code block from an LLM response."""
    patterns = [
        rf"```{framework}\s*([\s\S]*?)```",
        r"```typescript\s*([\s\S]*?)```",
        r"```javascript\s*([\s\S]*?)```",
        r"```js\s*([\s\S]*?)```",
        r"```\s*([\s\S]*?)```",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            if code and len(code) > 50 and not code.startswith(("## ", "# ")):
                return deduplicate_code(code)

    fixed_code_pattern = r"##\s*FIXED\s*CODE[:\s]*\n+([\s\S]+?)(?=\n##|\Z)"
    match = re.search(fixed_code_pattern, response, re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        code = re.sub(r"^```\w*\s*\n?", "", code)
        code = re.sub(r"\n?```\s*$", "", code)
        if code and len(code) > 50:
            return deduplicate_code(code.strip())

    return None


def deduplicate_code(code: str) -> str:
    """Remove duplicated import lines / test blocks an LLM may have generated."""
    require_pattern = r"^(const\s*\{\s*test.*\}\s*=\s*require\(['\"]@playwright/test['\"]\);)"
    import_pattern = r"^(import\s*\{.*\}\s*from\s*['\"]@playwright/test['\"];?)"

    for pattern in [require_pattern, import_pattern]:
        match = re.match(pattern, code, re.MULTILINE)
        if match:
            first_line = match.group(1)
            rest_of_code = code[len(first_line) :]
            if first_line in rest_of_code:
                duplicate_pos = rest_of_code.find(first_line)
                code = (first_line + rest_of_code[:duplicate_pos]).strip()
                logger.warning("Detected and removed duplicated test code")
                break

    test_matches = list(re.finditer(r"test\s*\(\s*['\"]", code))
    if len(test_matches) > 1:
        second_test_start = test_matches[1].start()
        code = code[:second_test_start].strip()
        if not code.rstrip().endswith("});"):
            code = code.rstrip() + "\n});"
        logger.warning("Detected and removed duplicate test() block")

    return code
