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
