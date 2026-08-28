"""Subscription-mode LLM access via installed coding-agent CLIs.

Developers often already pay for Claude Code / Codex / OpenCode subscriptions,
so 9lives can use those CLIs without asking for a new API key. Each agent CLI
carries its own login, so shelling out to its headless print mode inherits the
user's subscription with zero configuration:

    claude -p --output-format text   (prompt on stdin)
    codex exec <prompt>
    opencode run <prompt>

The response is parsed by the same CODE:/CHANGES: extractors as API-mode
Tier 2, so agent chatter around the answer is harmless.
"""

import logging
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

CALL_TIMEOUT_SECONDS = 180

# Ordered by how we invoke each supported agent CLI. The prompt travels on
# stdin wherever the CLI supports it — no shell-quoting, no arbitrary user text
# in argv, and no ARG_MAX ceiling. `claude -p` and `codex exec -` both take the
# prompt on stdin; `opencode run` has no stdin mode yet (upstream feature still
# open as of 2026), so its prompt stays a positional arg.
AGENT_COMMANDS: dict[str, dict] = {
    "claude-code": {"binary": "claude", "argv": ["-p", "--output-format", "text"], "prompt_via": "stdin"},
    "codex": {"binary": "codex", "argv": ["exec", "--skip-git-repo-check", "-"], "prompt_via": "stdin"},
    "opencode": {"binary": "opencode", "argv": ["run"], "prompt_via": "arg"},
}


def detect_agent_clis() -> list[str]:
    """Return the subscription providers whose CLI is on PATH, in preference order."""
    return [name for name, spec in AGENT_COMMANDS.items() if shutil.which(spec["binary"])]


def call_agent_cli(provider: str, system: str, user: str, timeout: int = CALL_TIMEOUT_SECONDS) -> str:
    """Run one headless prompt through an agent CLI and return its text output.

    Raises RuntimeError on missing binary, non-zero exit, or timeout — the
    caller decides whether to fall back to another provider.
    """
    spec = AGENT_COMMANDS.get(provider)
    if not spec:
        raise RuntimeError(f"Unknown agent CLI provider: {provider}")

    binary = shutil.which(spec["binary"])
    if not binary:
        raise RuntimeError(f"'{spec['binary']}' not found on PATH")

    # subprocess.run is always called with an argv LIST (never a shell string),
    # so shell metacharacters can't inject commands. For the argv-based provider
    # (opencode) the prompt leads with the trusted `system` preamble, so it also
    # can't be parsed as a CLI flag. The separate content-trust concern —
    # untrusted page text reaching a tool-capable agent — is documented in
    # README "Security & trust boundary".
    prompt = f"{system}\n\n{user}"
    argv = [binary, *spec["argv"]]
    run_kwargs: dict = {}
    if spec["prompt_via"] == "stdin":
        run_kwargs["input"] = prompt
    else:
        argv.append(prompt)
        # No stdin to send, but leaving it inherited makes agents that probe a
        # non-TTY stdin (codex/opencode) block forever waiting for EOF. Give them
        # an already-closed stdin.
        run_kwargs["stdin"] = subprocess.DEVNULL

    # Run in an empty scratch dir: print-mode agents may still glance at the
    # cwd, and the healing prompt is fully self-contained.
    scratch = tempfile.mkdtemp(prefix="ninelives-agent-")
    logger.info("Calling subscription CLI: %s", " ".join(argv[:3]))
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=scratch,
            **run_kwargs,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{spec['binary']} timed out after {timeout}s") from e

    if proc.returncode != 0:
        raise RuntimeError(f"{spec['binary']} exited {proc.returncode}: {proc.stderr[-500:]}")

    output = proc.stdout.strip()
    if not output:
        raise RuntimeError(f"{spec['binary']} produced no output")
    return output
