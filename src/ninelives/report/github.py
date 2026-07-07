"""GitHub-facing reports: step summary, action outputs, PR-comment body.

Port of the reporting idea in local-agent/go cmd_ci.go (ciWriteGitHubOutputs),
reshaped for the healing loop. Everything is plain-file based — the composite
action reads the comment body from disk and posts it with github-script, so
the CLI itself never talks to any API.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

COMMENT_BODY_FILENAME = ".9lives-report.md"
FOOTER = "🐾 checked by [9lives](https://9lives.run) — `curl -sL 9l.run | sh`"

_STATUS_EMOJI = {
    "passed": "✅",
    "healed": "🐾",
    "failed": "❌",
    "needs-human": "🙋",
}


@dataclass
class SpecOutcome:
    """One spec's journey through run/heal."""

    spec: str
    status: str  # passed | healed | failed | needs-human
    detail: str = ""  # first error line, or the healing change summary
    diff: str = ""  # unified diff when healed


def _longest_backtick_run(text: str) -> int:
    """Length of the longest consecutive run of backticks in text."""
    longest = run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    return longest


def render_markdown(outcomes: list[SpecOutcome], mode: str) -> str:
    """Render the report used for both the step summary and the PR comment."""
    healed = sum(1 for o in outcomes if o.status == "healed")
    failed = sum(1 for o in outcomes if o.status in ("failed", "needs-human"))
    passed = sum(1 for o in outcomes if o.status == "passed")

    if failed:
        verdict = f"❌ {failed} failing"
        if healed:
            verdict += f", {healed} healed"
    elif healed:
        verdict = f"🐾 {healed} test(s) came back to life"
    else:
        verdict = f"✅ all {passed} passing"

    lines = [f"## 🐾 9lives {mode} report — {verdict}", ""]
    lines.append("| spec | status | detail |")
    lines.append("|---|---|---|")
    for o in outcomes:
        emoji = _STATUS_EMOJI.get(o.status, "•")
        detail = (o.detail or "").replace("|", "\\|").replace("\n", " ")[:200]
        lines.append(f"| `{o.spec}` | {emoji} {o.status} | {detail} |")

    diffs = [o for o in outcomes if o.diff]
    if diffs:
        lines.append("")
        for o in diffs:
            body = o.diff.rstrip()
            # A spec can legitimately contain ``` (template literals, embedded
            # markdown). Fence with a backtick run longer than any inside the
            # diff so it can't break out of the code block.
            fence = "`" * max(3, _longest_backtick_run(body) + 1)
            lines.append(f"<details><summary>diff — {o.spec}</summary>\n")
            lines.append(f"{fence}diff")
            lines.append(body)
            lines.append(fence)
            lines.append("\n</details>")

    lines.extend(["", "---", FOOTER, ""])
    return "\n".join(lines)


def write_github_reports(outcomes: list[SpecOutcome], mode: str) -> None:
    """Write step summary + action outputs + comment body when running in CI.

    No-ops entirely outside GitHub Actions (no env vars set).
    """
    if not (os.environ.get("GITHUB_STEP_SUMMARY") or os.environ.get("GITHUB_OUTPUT")):
        return

    body = render_markdown(outcomes, mode)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(body + "\n")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        healed = sum(1 for o in outcomes if o.status == "healed")
        failed = sum(1 for o in outcomes if o.status in ("failed", "needs-human"))
        status = "failed" if failed else ("healed" if healed else "passed")
        with open(output_path, "a") as f:
            f.write(f"status={status}\nhealed={healed}\nfailed={failed}\n")

    comment_path = Path.cwd() / COMMENT_BODY_FILENAME
    comment_path.write_text(body)
    logger.info("Wrote PR comment body to %s", comment_path)
