"""Collect run artifacts to local disk.

Everything stays in .9lives/runs/<timestamp>/.

Also harvests Playwright's `error-context.md` (the page snapshot written on
failure since PW 1.50) — it stands in for the page HTML that powers Tier 1
offline healing.
"""

import logging
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg"}
VIDEO_SUFFIXES = {".webm", ".mp4"}

_CALL_LOG = re.compile(r"Call log:\n(.*?)```", re.DOTALL)
_PAGE_SNAPSHOT = re.compile(r"# Page snapshot\s+```yaml\n(.*?)```", re.DOTALL)


@dataclass
class Artifacts:
    run_dir: Path
    screenshots: list[Path] = field(default_factory=list)
    videos: list[Path] = field(default_factory=list)
    traces: list[Path] = field(default_factory=list)
    call_log: str = ""  # "waiting for locator(...)" lines — carries the failing selector
    page_snapshot: str = ""  # aria snapshot of the page at failure — Tier 1's search space


def parse_error_context(content: str) -> tuple[str, str]:
    """Split Playwright's error-context.md into (call_log, page_snapshot).

    The file also embeds the test source, which must NOT reach failure
    classification — expect() lines in healthy code read as assertion errors.
    """
    call_log_match = _CALL_LOG.search(content)
    snapshot_match = _PAGE_SNAPSHOT.search(content)
    return (
        call_log_match.group(1).strip() if call_log_match else "",
        snapshot_match.group(1).strip() if snapshot_match else "",
    )


def collect_artifacts(project_dir: Path, dest_root: Path) -> Artifacts:
    """Copy screenshots/videos/traces from test-results/ into a timestamped run dir."""
    run_dir = dest_root / "runs" / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts = Artifacts(run_dir=run_dir)

    results_dir = project_dir / "test-results"
    if not results_dir.is_dir():
        return artifacts

    for path in sorted(results_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in SCREENSHOT_SUFFIXES:
            artifacts.screenshots.append(_copy(path, run_dir))
        elif suffix in VIDEO_SUFFIXES:
            artifacts.videos.append(_copy(path, run_dir))
        elif suffix == ".zip" and "trace" in path.name.lower():
            artifacts.traces.append(_copy(path, run_dir))
        elif path.name == "error-context.md" and not artifacts.page_snapshot:
            artifacts.call_log, artifacts.page_snapshot = parse_error_context(path.read_text(errors="replace"))
            _copy(path, run_dir)

    logger.info(
        "Collected %d screenshots, %d videos, %d traces into %s",
        len(artifacts.screenshots),
        len(artifacts.videos),
        len(artifacts.traces),
        run_dir,
    )
    return artifacts


def _copy(src: Path, run_dir: Path) -> Path:
    dest = run_dir / src.name
    counter = 1
    while dest.exists():
        dest = run_dir / f"{src.stem}-{counter}{src.suffix}"
        counter += 1
    shutil.copy2(src, dest)
    return dest
