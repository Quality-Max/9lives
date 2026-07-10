"""Playwright adapter — thin wrapper over the original execution kernel."""

from pathlib import Path

from ..runner import execute
from ..runner.artifacts import Artifacts, collect_artifacts
from ..runner.execute import RunResult, ensure_project_ready


class PlaywrightAdapter:
    name = "playwright"
    language = "javascript"

    def preflight(self, spec: Path) -> None:
        ensure_project_ready(spec)

    def run(self, spec: Path) -> RunResult:
        return execute.run_spec(spec)

    def collect(self, result: RunResult, dest_root: Path) -> Artifacts | None:
        if result.project_dir is None:
            return None
        return collect_artifacts(result.project_dir, dest_root)
