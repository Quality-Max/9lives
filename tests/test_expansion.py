"""Tests for the expansion features: framework adapters (Cypress/Selenium),
heal history + brittle-selector report, the MCP server, and watch mode."""

import asyncio
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ninelives.frameworks import detect_framework, get_adapter  # noqa: E402
from ninelives.frameworks.cypress import parse_mocha_json  # noqa: E402
from ninelives.frameworks.selenium import parse_pytest_output  # noqa: E402
from ninelives.healing.parse import extract_failed_selector  # noqa: E402
from ninelives.healing.strategy import FailureType, TestFailure, healing_strategy_selector  # noqa: E402
from ninelives.healing.tier1 import tier1_healer  # noqa: E402


# ---------- framework detection ----------


def test_detect_framework_by_suffix(tmp_path):
    assert detect_framework(tmp_path / "login.cy.ts") == "cypress"
    assert detect_framework(tmp_path / "login.cy.js") == "cypress"
    assert detect_framework(tmp_path / "test_login.py") == "selenium"
    assert detect_framework(tmp_path / "login.spec.ts") == "playwright"  # bare spec, no project


def test_detect_framework_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"devDependencies": {"cypress": "13.0.0"}}')
    spec = tmp_path / "login.spec.js"
    spec.write_text("it('x', () => {});\n")
    assert detect_framework(spec) == "cypress"

    # A project with BOTH stays playwright — the .cy. naming is the cypress signal there.
    (tmp_path / "package.json").write_text('{"devDependencies": {"cypress": "13.0.0", "@playwright/test": "1.61.1"}}')
    assert detect_framework(spec) == "playwright"


def test_get_adapter_explicit_override_beats_detection(tmp_path):
    assert get_adapter(tmp_path / "login.spec.js", "selenium").name == "selenium"
    assert get_adapter(tmp_path / "login.cy.js", "auto").name == "cypress"


# ---------- cypress ----------

CYPRESS_LOCATOR_MSG = (
    "AssertionError: Timed out retrying after 4000ms: Expected to find element: `#login-btn`, but never found it."
)


def test_cypress_locator_miss_is_not_an_assertion():
    # Cypress wraps locator misses in AssertionError — the behavior-vs-drift
    # guard must NOT eat them; they are selector drift and healable.
    assert healing_strategy_selector.classify_failure(CYPRESS_LOCATOR_MSG) == FailureType.LOCATOR_NOT_FOUND


def test_cypress_selector_extraction():
    assert extract_failed_selector(CYPRESS_LOCATOR_MSG) == "#login-btn"
    assert extract_failed_selector("something failed", "cy.get('.submit-button').click()") == ".submit-button"


def test_parse_mocha_json_survives_banner_noise():
    stdout = (
        "It looks like this is your first time using Cypress\n"
        + json.dumps(
            {
                "stats": {"duration": 1234},
                "failures": [
                    {
                        "fullTitle": "login signs in",
                        "err": {"message": "Expected to find element: `#x`", "stack": "at ..."},
                    }
                ],
            }
        )
        + "\ntrailing noise"
    )
    errors, duration = parse_mocha_json(stdout)
    assert duration == 1234
    assert len(errors) == 1
    assert errors[0].title == "login signs in"
    assert "#x" in errors[0].message


# ---------- selenium ----------

SELENIUM_MSG = (
    "selenium.common.exceptions.NoSuchElementException: Message: no such element: "
    'Unable to locate element: {"method":"css selector","selector":"#submit-btn"}'
)


def test_selenium_no_such_element_classifies_as_locator():
    assert healing_strategy_selector.classify_failure(SELENIUM_MSG) == FailureType.LOCATOR_NOT_FOUND


def test_selenium_selector_extraction_from_json_payload():
    assert extract_failed_selector(SELENIUM_MSG) == "#submit-btn"


def test_selenium_selector_extraction_from_by_call():
    stack = 'driver.find_element(By.CSS_SELECTOR, "#old-btn").click()'
    assert extract_failed_selector("NoSuchElementException", stack) == "#old-btn"


def test_parse_pytest_output_extracts_failure():
    stdout = "\n".join(
        [
            "____________________ test_login ____________________",
            "",
            "    def test_login(driver):",
            '>       driver.find_element(By.CSS_SELECTOR, "#login-btn").click()',
            "",
            "E       " + SELENIUM_MSG,
            "",
            "FAILED test_login.py::test_login - selenium.common.exceptions.NoSuchElementException",
            "1 failed in 1.23s",
        ]
    )
    errors = parse_pytest_output(stdout)
    assert len(errors) == 1
    assert errors[0].title == "test_login"
    assert "NoSuchElementException" in errors[0].message
    assert "find_element" in errors[0].stack


def test_tier1_never_injects_playwright_waits_into_other_frameworks():
    base = dict(
        failure_type=FailureType.LOCATOR_TIMEOUT,
        error_message="Timeout 30000ms exceeded waiting for selector",
        failed_selector="button",  # immune to transformations → reaches the timing branch
        test_code="await page.locator('button').click();",
    )
    cypress = asyncio.run(tier1_healer.heal(TestFailure(**base, framework="cypress")))
    assert not cypress.success  # escalates instead of writing `await page.…` into Cypress code

    playwright = asyncio.run(tier1_healer.heal(TestFailure(**base, framework="playwright")))
    assert playwright.success
    assert "waitFor" in playwright.healed_code


# ---------- heal history / report ----------


def test_history_record_and_report(tmp_path):
    from ninelives.history import load_history, record_heal, render_report, selector_report

    spec = tmp_path / "app" / "login.spec.js"
    spec.parent.mkdir(parents=True)
    spec.write_text("x")

    record_heal(
        spec, framework="playwright", status="healed", failed_selector="#login", anchor="text", healed_selector="#signin"
    )
    record_heal(spec, framework="playwright", status="healed", failed_selector="#login", anchor="text")
    record_heal(spec, framework="playwright", status="needs-human", failed_selector=None, failure_type="assertion_failed")

    records = load_history(tmp_path)  # rglob finds the nested .9lives/history.jsonl
    assert len(records) == 3

    rows = selector_report(records)
    assert rows[0]["selector"] == "#login"
    assert rows[0]["heals"] == 2
    assert "data-testid" in rows[0]["recommendation"]  # healed 2× → pin something stable

    terminal = render_report(rows)
    assert "#login" in terminal
    markdown = render_report(rows, markdown=True)
    assert "| `#login` |" in markdown


def test_history_recording_never_breaks_healing(tmp_path, monkeypatch):
    # A read-only .9lives dir (or any history failure) must not crash the heal loop.
    from ninelives import cli
    from ninelives.frameworks import get_adapter

    spec = tmp_path / "login.spec.js"
    spec.write_text("x")
    monkeypatch.setattr("ninelives.history.record_heal", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    cli._record_history(spec, get_adapter(spec), "healed")  # must not raise


# ---------- MCP server ----------


def _mcp_roundtrip(messages):
    from ninelives import mcp_server

    stdin = io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
    stdout = io.StringIO()
    mcp_server.serve(stdin=stdin, stdout=stdout)
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def test_mcp_initialize_and_tools_list():
    responses = _mcp_roundtrip(
        [
            {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 2, "method": "nope/nope"},
        ]
    )
    assert responses[0]["result"]["protocolVersion"] == "2025-03-26"  # echoes the client's version
    assert responses[0]["result"]["serverInfo"]["name"] == "9lives"
    tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
    assert tool_names == {"heal_test", "run_test"}
    assert responses[2]["error"]["code"] == -32601


def test_mcp_heal_test_returns_structured_result(tmp_path, monkeypatch):
    from ninelives import cli
    from ninelives.report.github import SpecOutcome

    seen = {}

    def fake_heal_one(spec, **kwargs):
        seen.update(kwargs, spec=spec)
        print("progress chatter that must NOT hit the protocol stream")
        return SpecOutcome(spec=spec.name, status="healed", detail="not applied — saved", diff="--- a\n+++ b")

    monkeypatch.setattr(cli, "heal_one", fake_heal_one)
    spec = tmp_path / "login.spec.js"

    responses = _mcp_roundtrip(
        [
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "heal_test", "arguments": {"spec": str(spec)}},
            },
            {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "bogus", "arguments": {}}},
        ]
    )
    assert seen["interactive"] is False  # MCP must never block on input()
    assert seen["auto_apply"] is False

    result = responses[0]["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["status"] == "healed"
    assert payload["healed_copy"].endswith(".spec.js.healed")
    assert payload["applied"] is False
    assert "diff" in payload

    assert responses[1]["error"]["code"] == -32602


# ---------- watch ----------


def test_watch_scan_finds_specs_and_ignores_noise(tmp_path):
    from ninelives.watch import changed_specs, scan

    (tmp_path / "login.spec.js").write_text("x")
    (tmp_path / "checkout.cy.ts").write_text("x")
    (tmp_path / "test_flow.py").write_text("x")
    (tmp_path / "_9lives_heal_1_login.spec.js").write_text("x")  # our own working copy
    (tmp_path / "login.spec.js.healed").write_text("x")
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.spec.js").write_text("x")

    snapshot = scan([tmp_path])
    names = {p.name for p in snapshot}
    assert names == {"login.spec.js", "checkout.cy.ts", "test_flow.py"}

    import os

    target = tmp_path / "login.spec.js"
    os.utime(target, (target.stat().st_atime, target.stat().st_mtime + 5))
    changed = changed_specs(snapshot, scan([tmp_path]))
    assert [p.name for p in changed] == ["login.spec.js"]
