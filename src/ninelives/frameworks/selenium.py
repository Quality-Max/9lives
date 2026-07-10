"""Selenium adapter — run one Python Selenium spec through pytest.

Selenium has no single project convention, but in the Python world it
almost always runs under pytest — so that's the contract: a `.py` spec,
executed with the user's own pytest (their venv carries selenium and the
driver setup). Failures are parsed from pytest's text output; the
`NoSuchElementException` payload carries the failing selector.
"""

import logging
import re
import shutil
from pathlib import Path

from ..runner.execute import RUN_TIMEOUT_SECONDS, RunnerError, RunResult, TestError, _run

logger = logging.getLogger(__name__)

_SECTION_HEADER = re.compile(r"^_{3,}\s+(.+?)\s+_{3,}$")
_SUMMARY_LINE = re.compile(r"^(?:FAILED|ERROR)\s")


class SeleniumAdapter:
    name = "selenium"
    language = "python"

    def preflight(self, spec: Path) -> None:
        # Defense-in-depth for the agent-callable MCP path: run() below invokes
        # pytest via an argv list (never a shell), and the spec path is resolved
        # to an absolute path before being passed as an argument, so it can't be
        # parsed as a pytest flag or injected into a shell. Still, only .py files
        # make sense to run through pytest at all — reject anything else early,
        # before the PATH check, so this fails even without pytest installed.
        if spec.suffix.lower() != ".py":
            raise RunnerError(f"Selenium specs run through pytest and must be .py files (got {spec.name})")
        if shutil.which("pytest") is None:
            raise RunnerError(
                "'pytest' not found on PATH — Selenium specs run through your own pytest:\n"
                "    pip install pytest selenium\n"
                "then re-run 9lives from the environment your tests live in."
            )

    def run(self, spec: Path) -> RunResult:
        spec = spec.resolve()
        if not spec.is_file():
            raise RunnerError(f"Spec not found: {spec}")
        pytest_bin = shutil.which("pytest")
        if pytest_bin is None:
            raise RunnerError("'pytest' not found on PATH (see `9l doctor`)")

        cmd = [pytest_bin, str(spec), "--tb=long", "-q", "--color=no", "-p", "no:cacheprovider"]
        logger.info("Running: %s", " ".join(cmd))
        proc = _run(cmd, spec.parent, RUN_TIMEOUT_SECONDS)

        errors = parse_pytest_output(proc.stdout)
        passed = proc.returncode == 0
        if not passed and not errors:
            errors = [TestError(title=spec.name, message=(proc.stderr or proc.stdout)[-3000:])]

        return RunResult(
            passed=passed,
            exit_code=proc.returncode,
            errors=errors,
            stdout=proc.stdout,
            stderr=proc.stderr,
            project_dir=spec.parent,
        )

    def collect(self, result: RunResult, dest_root: Path):
        # No failure-time page snapshot — Selenium heals lean on the selector
        # embedded in the exception plus Tier 2.
        return None


def parse_pytest_output(stdout: str) -> list[TestError]:
    """Extract one TestError per failed test from pytest's -q text output.

    pytest separates failures with `____ test_name ____` headers; the
    exception itself arrives on `E   ...` lines. Everything else in the
    section is kept as the stack (it contains the failing source line,
    which selector extraction also scans).
    """
    errors: list[TestError] = []
    title: str | None = None
    message_lines: list[str] = []
    stack_lines: list[str] = []

    def flush() -> None:
        if title and message_lines:
            errors.append(
                TestError(
                    title=title,
                    message="\n".join(message_lines),
                    stack="\n".join(stack_lines)[-4000:],
                )
            )

    for line in stdout.splitlines():
        header = _SECTION_HEADER.match(line.strip())
        if header:
            flush()
            title = header.group(1)
            message_lines = []
            stack_lines = []
        elif _SUMMARY_LINE.match(line):
            flush()
            title = None
        elif title is not None:
            if line.startswith("E "):
                message_lines.append(line[1:].strip())
            else:
                stack_lines.append(line)
    flush()
    return errors
