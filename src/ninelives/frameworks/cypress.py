"""Cypress adapter — run one Cypress spec and parse the Mocha JSON report.

Cypress specs run inside the user's own Cypress project (no ephemeral
scaffolding — a Cypress install is ~700 MB of binary, so 9lives never
creates one behind the user's back). `--quiet` keeps stdout to the
reporter's JSON; a brace-scan fallback survives any preamble noise.
"""

import json
import logging
from pathlib import Path

from ..runner.execute import RUN_TIMEOUT_SECONDS, RunnerError, RunResult, TestError, _require, _run

logger = logging.getLogger(__name__)


class CypressAdapter:
    name = "cypress"
    language = "javascript"

    def preflight(self, spec: Path) -> None:
        if self.project_dir(spec) is None:
            raise RunnerError(
                "No Cypress project found around this spec. 9lives runs Cypress specs "
                "against your own project (it never scaffolds a Cypress install):\n"
                "    npm install -D cypress\n"
                "then re-run from inside the project."
            )

    def project_dir(self, spec: Path) -> Path | None:
        """Nearest ancestor whose package.json depends on cypress."""
        start = spec.resolve().parent
        for directory in [start, *start.parents]:
            package_json = directory / "package.json"
            if package_json.is_file():
                try:
                    data = json.loads(package_json.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "cypress" in deps:
                    return directory
        return None

    def run(self, spec: Path) -> RunResult:
        spec = spec.resolve()
        if not spec.is_file():
            raise RunnerError(f"Spec not found: {spec}")
        npx = _require("npx")
        project = self.project_dir(spec)
        if project is None:
            raise RunnerError("No Cypress project found (package.json with a cypress dependency)")

        cmd = [npx, "cypress", "run", "--spec", str(spec), "--reporter", "json", "--quiet"]
        logger.info("Running: %s (cwd=%s)", " ".join(cmd), project)
        proc = _run(cmd, project, RUN_TIMEOUT_SECONDS)

        errors, duration_ms = parse_mocha_json(proc.stdout)
        passed = proc.returncode == 0
        if not passed and not errors:
            errors = [TestError(title=spec.name, message=(proc.stderr or proc.stdout)[-3000:])]

        return RunResult(
            passed=passed,
            exit_code=proc.returncode,
            errors=errors,
            stdout=proc.stdout,
            stderr=proc.stderr,
            project_dir=project,
            duration_ms=duration_ms,
        )

    def collect(self, result: RunResult, dest_root: Path):
        # Cypress writes no failure-time page snapshot, so there is nothing to
        # feed Tier 1's anchor search — heals rely on selector transformations
        # and Tier 2. Screenshots stay where Cypress puts them.
        return None


def parse_mocha_json(stdout: str) -> tuple[list[TestError], int]:
    """Extract failures from Mocha's JSON reporter output on stdout.

    Cypress may still print banners around the JSON, so scan for the
    outermost braces instead of trusting the whole stream.
    """
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end <= start:
        return [], 0
    try:
        report = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return [], 0

    errors: list[TestError] = []
    for failure in report.get("failures", []):
        err = failure.get("err", {}) or {}
        errors.append(
            TestError(
                title=failure.get("fullTitle") or failure.get("title", "unknown"),
                message=err.get("message", ""),
                stack=err.get("stack", ""),
            )
        )
    duration_ms = int(report.get("stats", {}).get("duration", 0) or 0)
    return errors, duration_ms
