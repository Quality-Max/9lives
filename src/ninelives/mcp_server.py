"""`9l mcp` — 9lives as an MCP server for coding agents.

Claude Code / Cursor / Codex can call `heal_test` mid-session: the agent
ships a change, a spec goes red, and it heals in-loop instead of waiting
for CI. Zero dependencies: MCP's stdio transport is newline-delimited
JSON-RPC 2.0, small enough to speak directly.

    claude mcp add 9lives -- 9l mcp

Protocol notes: stdout carries ONLY protocol frames; all heal-loop output
is redirected to stderr (which MCP hosts surface as server logs).
"""

import contextlib
import json
import logging
import sys
from pathlib import Path

from . import __version__

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"

SERVER_INFO = {"name": "9lives", "title": "9lives — self-healing tests", "version": __version__}

INSTRUCTIONS = (
    "Self-healing test runner. Call heal_test when a Playwright/Cypress/Selenium spec fails: "
    "it re-runs the spec, repairs drifted selectors (offline Tier 1, LLM Tier 2), verifies green, "
    "and returns the diff. With apply=false the fix is saved next to the spec as <spec>.healed "
    "for you to review/apply; with apply=true it is written in place. "
    "A needs-human status usually means a failing assertion — a possible real bug 9lives refuses to mask."
)

TOOLS = [
    {
        "name": "heal_test",
        "title": "Heal a failing test",
        "description": (
            "Run a test spec and self-heal it if it fails (selector drift, timing). Returns status "
            "(passed | healed | failed | needs-human), the unified diff, and where the healed code went. "
            "needs-human means the failure looks like a real behavior change — do not force the test green."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {"type": "string", "description": "Path to the spec file (.spec.ts, .cy.js, test_*.py …)"},
                "apply": {
                    "type": "boolean",
                    "default": False,
                    "description": "Write the healed code to the spec in place (default: save a .healed copy)",
                },
                "max_iterations": {"type": "integer", "default": 3, "minimum": 1, "maximum": 9},
                "framework": {
                    "type": "string",
                    "enum": ["auto", "playwright", "cypress", "selenium"],
                    "default": "auto",
                },
            },
            "required": ["spec"],
        },
    },
    {
        "name": "run_test",
        "title": "Run a test",
        "description": "Run a test spec without healing. Returns pass/fail and the failure details.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {"type": "string", "description": "Path to the spec file"},
                "framework": {
                    "type": "string",
                    "enum": ["auto", "playwright", "cypress", "selenium"],
                    "default": "auto",
                },
            },
            "required": ["spec"],
        },
    },
]


def serve(stdin=None, stdout=None) -> int:
    """Blocking newline-delimited JSON-RPC loop. Returns on EOF."""
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            _send(stdout, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        response = _handle(message)
        if response is not None:
            _send(stdout, response)
    return 0


def _send(stdout, payload: dict) -> None:
    stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stdout.flush()


def _handle(message: dict):
    """Dispatch one JSON-RPC message; returns a response dict or None for notifications."""
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params") or {}
    is_notification = "id" not in message

    if method == "initialize":
        return _result(
            msg_id,
            {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            },
        )
    if method.startswith("notifications/"):
        return None
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        return _call_tool(msg_id, params)
    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def _result(msg_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _tool_text(msg_id, payload: dict, is_error: bool = False) -> dict:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    return _result(msg_id, {"content": [{"type": "text", "text": text}], "isError": is_error})


def _call_tool(msg_id, params: dict) -> dict:
    from .runner.execute import RunnerError

    name = params.get("name")
    args = params.get("arguments") or {}
    try:
        if name == "heal_test":
            return _tool_text(msg_id, _heal_test(args))
        if name == "run_test":
            return _tool_text(msg_id, _run_test(args))
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
    except RunnerError as e:
        return _tool_text(msg_id, {"error": str(e)}, is_error=True)
    except Exception as e:  # tool failures must come back as results, not crash the server
        logger.exception("tool %s failed", name)
        return _tool_text(msg_id, {"error": f"{type(e).__name__}: {e}"}, is_error=True)


def _heal_test(args: dict) -> dict:
    from .cli import heal_one

    spec = Path(args["spec"]).expanduser()
    apply = bool(args.get("apply", False))
    # The heal loop prints progress to stdout, which would corrupt the
    # protocol stream — reroute it to stderr (host shows it as server logs).
    with contextlib.redirect_stdout(sys.stderr):
        outcome = heal_one(
            spec,
            auto_apply=apply,
            max_iterations=int(args.get("max_iterations", 3)),
            framework=args.get("framework", "auto"),
            interactive=False,
        )
    payload = {
        "spec": str(spec),
        "status": outcome.status,
        "detail": outcome.detail,
        "applied": apply and outcome.status == "healed",
    }
    if outcome.status == "healed" and not apply:
        payload["healed_copy"] = str(spec.with_suffix(spec.suffix + ".healed"))
    if outcome.diff:
        payload["diff"] = outcome.diff
    if outcome.status == "needs-human":
        payload["note"] = "possible real bug — 9lives refuses to rewrite assertions to force a pass"
    return payload


def _run_test(args: dict) -> dict:
    from .cli import run_one

    spec = Path(args["spec"]).expanduser()
    with contextlib.redirect_stdout(sys.stderr):
        outcome = run_one(spec, framework=args.get("framework", "auto"))
    return {"spec": str(spec), "status": outcome.status, "detail": outcome.detail}
