"""Run a Playwright spec and parse the JSON report.

The execution kernel: npm install (scaffolded projects only) →
`npx playwright install chromium` on demand → `npx playwright test` with the
JSON reporter → structured RunResult.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .project import find_enclosing_package_json, find_user_project, scaffold_project

logger = logging.getLogger(__name__)

RUN_TIMEOUT_SECONDS = 300
INSTALL_TIMEOUT_SECONDS = 600

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(text: str) -> str:
    return _ANSI.sub("", text or "")


@dataclass
class TestError:
    """One failing test extracted from the Playwright JSON report."""

    title: str
    message: str
    stack: str = ""
    snippet: str = ""


@dataclass
class RunResult:
    """Outcome of one `npx playwright test` invocation."""

    passed: bool
    exit_code: int
    errors: list[TestError] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    project_dir: Path | None = None
    results_json: Path | None = None
    duration_ms: int = 0


class RunnerError(RuntimeError):
    """Environment problem that prevents running at all (no node, npm failed…)."""


def _require(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise RunnerError(f"'{binary}' not found on PATH — install Node.js >= 18 (see `9l doctor`)")
    return path


def _run(cmd: list[str], cwd: Path, timeout: int, env: dict | None = None) -> subprocess.CompletedProcess:
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=merged_env)


def ensure_browsers(project_dir: Path) -> None:
    """Install chromium if Playwright reports it missing."""
    if os.environ.get("NINELIVES_CHROMIUM_PATH"):
        return  # user supplied a browser binary; nothing to install
    npx = _require("npx")
    check = _run([npx, "playwright", "install", "--dry-run", "chromium"], project_dir, 60)
    if "is already installed" in (check.stdout + check.stderr):
        return
    logger.info("Installing chromium for Playwright…")
    result = _run([npx, "playwright", "install", "chromium"], project_dir, INSTALL_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise RunnerError(f"playwright install chromium failed:\n{result.stderr[-2000:]}")


def ensure_project_ready(spec_path: Path) -> None:
    """Preflight: fail fast with actionable advice when the spec lives in a Node
    project that hasn't installed @playwright/test.

    Without this, `find_user_project` returns None (it only matches a package.json
    that *depends on* @playwright/test), 9lives silently scaffolds a detached
    project, and the spec's own fixture/helper imports fail — which `heal` then
    tries to "fix", masking the real problem (Playwright just isn't installed).
    A bare spec with no enclosing package.json is fine — that scaffolds correctly.
    """
    spec_path = spec_path.resolve()
    if find_user_project(spec_path.parent) is not None:
        return  # real Playwright project — good to go
    enclosing = find_enclosing_package_json(spec_path.parent)
    if enclosing is not None:
        raise RunnerError(
            f"{enclosing / 'package.json'} exists but does not depend on @playwright/test.\n"
            "9lives runs your spec against your own Playwright project — install it first:\n"
            "    npm install -D @playwright/test && npx playwright install\n"
            "then re-run 9lives. (Standalone specs with no enclosing package.json are "
            "scaffolded automatically.)"
        )


def run_spec(spec_path: Path, workdir: Path | None = None) -> RunResult:
    """Run one spec file. Uses the user's own Playwright project when one
    encloses the spec; otherwise scaffolds an ephemeral project."""
    spec_path = spec_path.resolve()
    if not spec_path.is_file():
        raise RunnerError(f"Spec not found: {spec_path}")

    npx = _require("npx")

    user_project = find_user_project(spec_path.parent)
    if user_project:
        project_dir = user_project
        spec_arg = str(spec_path.relative_to(user_project))
        results_path = Path(tempfile.mkdtemp(prefix="ninelives-")) / "results.json"
    else:
        project_dir = workdir or Path(tempfile.mkdtemp(prefix="ninelives-"))
        scaffold_project(project_dir, spec_path)
        spec_arg = spec_path.name
        results_path = project_dir / "results.json"
        install = _run(["npm", "install", "--no-audit", "--no-fund"], project_dir, INSTALL_TIMEOUT_SECONDS)
        if install.returncode != 0:
            raise RunnerError(f"npm install failed:\n{install.stderr[-2000:]}")

    ensure_browsers(project_dir)

    env = {"PLAYWRIGHT_JSON_OUTPUT_NAME": str(results_path), "CI": "1"}
    cmd = [npx, "playwright", "test", spec_arg, "--reporter=json"]
    logger.info("Running: %s (cwd=%s)", " ".join(cmd), project_dir)
    proc = _run(cmd, project_dir, RUN_TIMEOUT_SECONDS, env=env)

    errors, duration_ms = _parse_report(results_path, proc.stdout)
    passed = proc.returncode == 0

    if not passed and not errors:
        # Report missing or unparseable — fall back to raw output as the error.
        errors = [TestError(title=spec_path.name, message=(proc.stderr or proc.stdout)[-3000:])]

    return RunResult(
        passed=passed,
        exit_code=proc.returncode,
        errors=errors,
        stdout=proc.stdout,
        stderr=proc.stderr,
        project_dir=project_dir,
        results_json=results_path if results_path.exists() else None,
        duration_ms=duration_ms,
    )


def _parse_report(results_path: Path, stdout: str) -> tuple[list[TestError], int]:
    """Extract failing tests from a Playwright JSON report (file or stdout)."""
    raw = None
    if results_path.exists():
        raw = results_path.read_text()
    elif stdout.lstrip().startswith("{"):
        raw = stdout

    if not raw:
        return [], 0

    try:
        report = json.loads(raw)
    except json.JSONDecodeError:
        return [], 0

    errors: list[TestError] = []
    duration_ms = int(report.get("stats", {}).get("duration", 0))

    def walk(suite: dict) -> None:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                for result in test.get("results", []):
                    if result.get("status") in ("failed", "timedOut"):
                        error = result.get("error", {}) or {}
                        errors.append(
                            TestError(
                                title=spec.get("title", "unknown"),
                                message=_clean(error.get("message", "")),
                                stack=_clean(error.get("stack", "")),
                                snippet=_clean(error.get("snippet", "")),
                            )
                        )
        for child in suite.get("suites", []):
            walk(child)

    for suite in report.get("suites", []):
        walk(suite)

    return errors, duration_ms
