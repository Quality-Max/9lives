"""9lives CLI — `9l` / `9lives`.

Commands:
    9l run <spec>      Run a Playwright spec locally, artifacts in .9lives/
    9l heal <spec>     Run → classify → Tier 1 (offline) → Tier 2 (your key)
                       → re-run → show diff → apply on confirm
    9l doctor          Check node/npx/playwright/API keys
"""

import argparse
import asyncio
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__
from .healing.parse import extract_failed_selector
from .healing.patch import diff_stats, generate_unified_diff
from .healing.strategy import FailureType, HealingTier, TestFailure, healing_strategy_selector
from .healing.tier1 import tier1_healer
from .healing.tier2 import Tier2AISuggest
from .llm.agent_cli import detect_agent_clis
from .llm.client import LLMClient
from .report.github import SpecOutcome, write_github_reports
from .runner.artifacts import collect_artifacts
from .runner.execute import RunnerError, ensure_project_ready, run_spec
from .runner.project import find_user_project

logger = logging.getLogger(__name__)

MAX_HEALING_ITERATIONS = 3
PAW = "\U0001f43e"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="9l", description="9lives — your tests have nine lives. https://9lives.run")
    parser.add_argument("--version", action="version", version=f"9lives {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run Playwright specs locally")
    run_parser.add_argument("specs", type=Path, nargs="+")

    heal_parser = sub.add_parser("heal", help="run specs and heal them if they fail")
    heal_parser.add_argument("specs", type=Path, nargs="+")
    heal_parser.add_argument("-y", "--yes", action="store_true", help="apply healed code without confirmation")
    heal_parser.add_argument("--max-iterations", type=int, default=MAX_HEALING_ITERATIONS)

    sub.add_parser("doctor", help="check environment prerequisites")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        if args.command == "run":
            return cmd_run(args.specs)
        if args.command == "heal":
            return cmd_heal(args.specs, auto_apply=args.yes, max_iterations=args.max_iterations)
        if args.command == "doctor":
            return cmd_doctor()
    except RunnerError as e:
        print(f"{PAW} error: {e}", file=sys.stderr)
        return 2
    return 0


def _dest_root(spec: Path) -> Path:
    return spec.resolve().parent / ".9lives"


def cmd_run(specs: list[Path]) -> int:
    outcomes = []
    exit_code = 0
    for spec in specs:
        outcome = run_one(spec)
        outcomes.append(outcome)
        if outcome.status != "passed":
            exit_code = 1
    write_github_reports(outcomes, "run")
    return exit_code


def run_one(spec: Path) -> SpecOutcome:
    ensure_project_ready(spec)
    print(f"{PAW} running {spec} …")
    result = run_spec(spec)
    artifacts = collect_artifacts(result.project_dir, _dest_root(spec)) if result.project_dir else None

    if result.passed:
        print(f"{PAW} PASSED in {result.duration_ms / 1000:.1f}s")
        return SpecOutcome(spec=spec.name, status="passed", detail=f"{result.duration_ms / 1000:.1f}s")

    print(f"{PAW} FAILED ({len(result.errors)} failing test(s))")
    first_line = ""
    for error in result.errors:
        first_line = error.message.splitlines()[0] if error.message else "(no message)"
        print(f"\n  ✗ {error.title}\n    {first_line}")
    if artifacts and (artifacts.screenshots or artifacts.traces):
        print(f"\n  artifacts: {artifacts.run_dir}")
    return SpecOutcome(spec=spec.name, status="failed", detail=first_line)


def cmd_heal(specs: list[Path], auto_apply: bool = False, max_iterations: int = MAX_HEALING_ITERATIONS) -> int:
    outcomes = []
    exit_code = 0
    for spec in specs:
        outcome = heal_one(spec, auto_apply=auto_apply, max_iterations=max_iterations)
        outcomes.append(outcome)
        if outcome.status in ("failed", "needs-human"):
            exit_code = 1
    write_github_reports(outcomes, "heal")
    return exit_code


def heal_one(spec: Path, auto_apply: bool = False, max_iterations: int = MAX_HEALING_ITERATIONS) -> SpecOutcome:
    spec = spec.resolve()
    ensure_project_ready(spec)  # fail fast on a project missing @playwright/test, before scaffolding/healing
    # Heal against a working copy so the user's own file is only touched after
    # approval. When the spec lives inside a real Playwright project, that copy
    # MUST stay a sibling of the original — otherwise its playwright.config
    # (baseURL, projects, globalSetup), relative fixture imports, and testMatch
    # don't resolve and every heal re-run would misfire in a bare scaffold.
    # Only truly project-less specs fall back to an ephemeral temp dir.
    if find_user_project(spec.parent):
        working_spec = spec.with_name(f"_9lives_heal_{os.getpid()}_{spec.name}")
    else:
        working_spec = Path(tempfile.mkdtemp(prefix="ninelives-heal-")) / spec.name

    try:
        return _heal_loop(spec, working_spec, auto_apply=auto_apply, max_iterations=max_iterations)
    finally:
        # The sibling copy lives in the user's tree; never leave it behind.
        if working_spec.parent == spec.parent and working_spec.exists():
            working_spec.unlink()


def _heal_loop(spec: Path, working_spec: Path, *, auto_apply: bool, max_iterations: int) -> SpecOutcome:
    original_code = spec.read_text()
    current_code = original_code
    working_spec.write_text(current_code)

    tier2 = Tier2AISuggest()
    healed = False
    tier1_used = False  # Tier 1 gets one shot per session; a still-failing test escalates
    last_changes: list[str] = []

    for iteration in range(1, max_iterations + 1):
        print(f"{PAW} run {iteration}/{max_iterations}: {spec.name} …")
        result = run_spec(working_spec)

        if result.passed:
            if iteration == 1:
                print(f"{PAW} already passing — nothing to heal.")
                return SpecOutcome(spec=spec.name, status="passed", detail="already passing")
            healed = True
            break

        error = result.errors[0]
        artifacts = collect_artifacts(result.project_dir, _dest_root(spec)) if result.project_dir else None
        # error-context.md carries the call log (the failing selector) and the
        # page snapshot (where Tier 1 finds the element's new identity).
        call_log = artifacts.call_log if artifacts else ""
        page_snapshot = artifacts.page_snapshot if artifacts else ""

        failure = TestFailure(
            failure_type=healing_strategy_selector.classify_failure(error.message, error.stack + "\n" + call_log),
            error_message=error.message,
            failed_selector=extract_failed_selector(error.message, error.stack + "\n" + call_log),
            stack_trace=error.stack,
            test_code=current_code,
            page_html=page_snapshot,
        )
        tier = healing_strategy_selector.select_strategy(failure)
        print(f"  failure: {failure.failure_type.value} (selector: {failure.failed_selector or 'n/a'}) → {tier.value}")

        if tier == HealingTier.TIER1_AUTO and tier1_used:
            # Tier 1 had its shot and the test still fails — don't loop on
            # blind selector transforms, escalate to the LLM.
            print("  tier 1 already attempted, escalating to tier 2 …")
            healing = asyncio.run(tier2.suggest(failure))
        elif tier == HealingTier.TIER1_AUTO:
            tier1_used = True
            healing = asyncio.run(tier1_healer.heal(failure))
            if not healing.success:
                print(f"  tier 1 could not heal ({healing.metadata.get('reason')}), escalating to tier 2 …")
                healing = asyncio.run(tier2.suggest(failure))
        elif tier == HealingTier.TIER2_AI_SUGGEST:
            healing = asyncio.run(tier2.suggest(failure))
        else:
            if failure.failure_type == FailureType.ASSERTION_FAILED:
                # Behavior-vs-drift guard: never rewrite a failing assertion to
                # force a pass — that hides a real bug. Flag it for a human.
                print(f"{PAW} possible real bug — an assertion failed (behavior changed, not a selector).")
                print("   9lives won't rewrite assertions to force a pass. Review it, or set")
                print("   NINELIVES_HEAL_ASSERTIONS=1 to let Tier 2 propose an assertion update.")
            else:
                print(f"{PAW} this failure needs a human ({tier.value}) — no automatic fix attempted.")
            return SpecOutcome(
                spec=spec.name,
                status="needs-human",
                detail=f"{failure.failure_type.value}: {error.message.splitlines()[0] if error.message else ''}",
            )

        if not healing.success or not healing.healed_code:
            reason = healing.metadata.get("reason", "no fix produced")
            print(f"{PAW} could not heal: {reason}")
            return SpecOutcome(spec=spec.name, status="failed", detail=f"unhealed — {reason}")

        last_changes = healing.changes_made
        for change in last_changes:
            print(f"  {healing.tier.value}: {change} (confidence {healing.confidence:.0%})")

        current_code = healing.healed_code
        working_spec.write_text(current_code)

    # The heal produced on the final loop pass was written but not yet re-run
    # (each earlier heal is verified by the next pass's run). Verify it here so
    # the last attempt — and every attempt when --max-iterations=1 — can report
    # success instead of a false "still failing after N attempts".
    if not healed and current_code != original_code:
        print(f"{PAW} verifying final heal …")
        if run_spec(working_spec).passed:
            healed = True

    if not healed:
        print(f"{PAW} still failing after {max_iterations} heal attempts. Artifacts in {_dest_root(spec)}")
        return SpecOutcome(spec=spec.name, status="failed", detail=f"still failing after {max_iterations} heal attempts")

    diff = generate_unified_diff(original_code, current_code, script_name=spec.name)
    stats = diff_stats(diff)
    print(f"\n{PAW} healed! (+{stats['lines_added']} / -{stats['lines_removed']})\n")
    print(diff)
    detail = "; ".join(last_changes)[:200] if last_changes else "selector healed"

    if not auto_apply:
        answer = input(f"apply to {spec}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            healed_copy = spec.with_suffix(spec.suffix + ".healed")
            healed_copy.write_text(current_code)
            print(f"{PAW} not applied — healed copy saved to {healed_copy}")
            return SpecOutcome(spec=spec.name, status="healed", detail=f"not applied — saved to {healed_copy.name}", diff=diff)

    spec.write_text(current_code)
    print(f"{PAW} applied. Your test came back to life.")
    return SpecOutcome(spec=spec.name, status="healed", detail=detail, diff=diff)


def cmd_doctor() -> int:
    checks: list[tuple[str, bool, str]] = []

    node = shutil.which("node")
    node_version = ""
    if node:
        try:
            node_version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            node_version = "found but not responding"
    checks.append(("node", bool(node), node_version or "not found — install Node.js >= 18"))
    checks.append(("npx", bool(shutil.which("npx")), "" if shutil.which("npx") else "not found"))

    clis = detect_agent_clis()
    checks.append(
        (
            "agent",
            bool(clis),
            ", ".join(clis) + " (subscription — used for Tier 2)"
            if clis
            else "no coding-agent CLI found (claude / codex / opencode)",
        )
    )

    client = LLMClient()
    if client.is_subscription:
        detail = f"not needed — using your {client.provider} subscription"
        key_ok = True
    elif client.available:
        detail = f"{client.provider} ({client.model})"
        key_ok = True
    else:
        detail = "none — Tier 1 offline healing still works; set ANTHROPIC_API_KEY or OPENAI_API_KEY for Tier 2"
        key_ok = False
    checks.append(("LLM key", key_ok, detail))

    all_ok = True
    for name, ok, detail in checks:
        mark = "✓" if ok else "✗"
        print(f" {mark} {name:<8} {detail}")
        if name in ("node", "npx") and not ok:
            all_ok = False

    print(f"\n{PAW} {'ready' if all_ok else 'not ready — fix the items above'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
