"""Unified diffs for healing patches."""

from __future__ import annotations

import difflib


def generate_unified_diff(
    original: str,
    healed: str,
    script_name: str = "script.ts",
    context_lines: int = 5,
) -> str:
    """Return a unified diff string comparing original to healed code."""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        healed.splitlines(keepends=True),
        fromfile=f"a/{script_name}",
        tofile=f"b/{script_name}",
        n=context_lines,
    )
    return "".join(diff)


def diff_stats(diff: str) -> dict[str, int]:
    """Count added/removed lines from a unified diff string."""
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return {"lines_added": added, "lines_removed": removed}


_COMMENT_PREFIXES = ("//", "#", "/*", "*", "*/", "<!--", "-->")


def changed_lines(original: str, healed: str) -> list[str]:
    """Every line added or removed between original and healed (no context)."""
    diff = list(difflib.unified_diff(original.splitlines(), healed.splitlines(), n=0, lineterm=""))
    # Skip the two file headers; hunk headers start with "@@".
    return [line[1:] for line in diff[2:] if line[:1] in "+-"]


def comments_changed(original: str, healed: str) -> bool:
    """True when an edit adds or removes any comment or blank line.

    Tier 2 is allowed to fix failing code, not rewrite surrounding prose. Reject
    comment edits even when a real code change accompanies them, so fabricated
    claims cannot ride along with an otherwise valid locator fix.
    """
    return any(_is_comment_or_blank(line) for line in changed_lines(original, healed))


def _is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return stripped == "" or stripped.startswith(_COMMENT_PREFIXES)
