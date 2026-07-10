"""`9l watch` — heal on save.

Polls spec files for changes (zero dependencies, works everywhere) and runs
the heal loop on whatever changed — so healing becomes part of the local
edit-save loop, not just a CI afterthought.
"""

import logging
import os
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 1.0

# What counts as a spec file when watching a directory.
SPEC_NAME = re.compile(
    r"(\.(spec|test)\.[cm]?[jt]sx?$)|(\.cy\.[cm]?[jt]sx?$)|(^test_.*\.py$)|(_test\.py$)",
    re.IGNORECASE,
)

IGNORED_DIRS = {
    "node_modules",
    ".git",
    ".9lives",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "test-results",
    "playwright-report",
    "cypress",  # cypress/{videos,screenshots,downloads} churn on every run
}


def is_spec_file(path: Path) -> bool:
    name = path.name
    if name.startswith("_9lives_heal_") or name.endswith(".healed"):
        return False  # our own working copies / saved heals
    return bool(SPEC_NAME.search(name))


def scan(targets: list[Path]) -> dict[Path, float]:
    """Snapshot mtimes of every watched spec file."""
    snapshot: dict[Path, float] = {}
    for target in targets:
        target = target.resolve()
        if target.is_file():
            if is_spec_file(target):
                snapshot[target] = target.stat().st_mtime
            continue
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
            for filename in filenames:
                path = Path(dirpath) / filename
                if is_spec_file(path):
                    try:
                        snapshot[path] = path.stat().st_mtime
                    except OSError:
                        continue
    return snapshot


def changed_specs(before: dict[Path, float], after: dict[Path, float]) -> list[Path]:
    """Files that are new or have a newer mtime, oldest change first."""
    changed = [path for path, mtime in after.items() if mtime > before.get(path, -1.0)]
    return sorted(changed, key=lambda p: after[p])


def watch_loop(targets: list[Path], on_change, interval: float = DEFAULT_INTERVAL_SECONDS) -> int:
    """Poll until Ctrl-C, invoking `on_change(path)` for each changed spec.

    After the callback runs, the snapshot is re-taken so a heal that writes
    the spec back doesn't re-trigger itself.
    """
    snapshot = scan(targets)
    print(f"🐾 watching {len(snapshot)} spec file(s) — save a file to heal it (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(interval)
            current = scan(targets)
            for path in changed_specs(snapshot, current):
                # Let the editor finish writing before we run.
                time.sleep(0.2)
                on_change(path)
            snapshot = scan(targets)
    except KeyboardInterrupt:
        print("\n🐾 watch stopped.")
        return 0
