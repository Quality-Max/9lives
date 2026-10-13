"""Python integrations select the Python CLI even when a Go 9l is on PATH."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


def test_python_integration_commands_ignore_foreign_9l(tmp_path):
    """A Go executable earlier on PATH must not change Python integration identity."""
    executable(tmp_path / "9l", "#!/bin/sh\necho 'wrong engine' >&2\nexit 97\n")
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "PYTHONPATH": str(ROOT / "src"),
    }
    hook_entries = [
        line.removeprefix("  entry: ")
        for line in (ROOT / ".pre-commit-hooks.yaml").read_text().splitlines()
        if line.startswith("  entry: ")
    ]
    action_entries = [
        line.strip().split(' "${specs[@]}"')[0]
        for line in (ROOT / "action" / "action.yml").read_text().splitlines()
        if "ninelives.cli" in line
    ]
    assert len(hook_entries) == len(action_entries) == 2
    for entry in hook_entries + action_entries:
        command = shlex.split(entry)
        assert command[1:3] == ["-m", "ninelives.cli"]
        result = subprocess.run(
            [sys.executable, *command[1:3], "--version"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "9lives 0.2.1"
