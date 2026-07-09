"""Unit tests for the lifted healing core (pure, no network)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ninelives.healing.parse import deduplicate_code, extract_code_from_response, extract_failed_selector  # noqa: E402
from ninelives.healing.patch import diff_stats, generate_unified_diff  # noqa: E402
from ninelives.healing.strategy import FailureType, HealingTier, TestFailure, healing_strategy_selector  # noqa: E402
from ninelives.healing.tier1 import tier1_healer  # noqa: E402
from ninelives.runner.artifacts import parse_error_context  # noqa: E402
from ninelives.runner.execute import RunnerError, ensure_project_ready  # noqa: E402


def test_classify_locator_failure():
    failure_type = healing_strategy_selector.classify_failure(
        "TimeoutError: locator.click: Timeout 30000ms exceeded.\nwaiting for locator('#login-btn')"
    )
    assert failure_type in (FailureType.LOCATOR_NOT_FOUND, FailureType.LOCATOR_TIMEOUT)


def test_classify_assertion_failure():
    failure_type = healing_strategy_selector.classify_failure("Error: expect(received).toBe(expected)")
    assert failure_type == FailureType.ASSERTION_FAILED


def test_classify_syntax_error():
    failure_type = healing_strategy_selector.classify_failure("SyntaxError: Unexpected token '}'")
    assert failure_type == FailureType.SYNTAX_ERROR
    failure = TestFailure(failure_type=failure_type, error_message="SyntaxError")
    assert healing_strategy_selector.select_strategy(failure) == HealingTier.NO_HEALING


def test_extract_failed_selector():
    message = "TimeoutError: locator.click: Timeout 30000ms exceeded.\nwaiting for locator('#login-btn')"
    assert extract_failed_selector(message) == "#login-btn"

    message2 = "Error: page.locator(\"[data-testid='submit']\").click: element not found"
    assert extract_failed_selector(message2) == "[data-testid='submit']"


def test_tier1_heals_moved_id_from_page_snapshot():
    """The hero scenario: selector drifted, the element still exists under a new id."""
    failure = TestFailure(
        failure_type=FailureType.LOCATOR_NOT_FOUND,
        error_message="waiting for locator('#login-btn')",
        failed_selector="#login-btn",
        test_code="await page.locator('#login-btn').click();",
        page_html='<button id="login-btn-v2" class="btn primary">Sign in</button>',
    )
    result = asyncio.run(tier1_healer.heal(failure))
    assert result.success
    assert "#login-btn-v2" in result.healed_code
    assert result.confidence >= 0.7


def test_tier1_selects_tier1_when_alternative_findable():
    failure = TestFailure(
        failure_type=FailureType.LOCATOR_NOT_FOUND,
        error_message="waiting for locator",
        failed_selector="text='Submit'",
        test_code="await page.locator(\"text='Submit'\").click();",
        page_html="<button>Submit</button>",
    )
    assert healing_strategy_selector.select_strategy(failure) == HealingTier.TIER1_AUTO


def test_unified_diff_and_stats():
    diff = generate_unified_diff("a\nb\n", "a\nc\n", script_name="x.spec.ts")
    assert "-b" in diff and "+c" in diff
    stats = diff_stats(diff)
    assert stats == {"lines_added": 1, "lines_removed": 1}


def test_extract_code_from_response():
    response = (
        "REASONING: selector changed\nCHANGES:\n- updated selector\nCODE:\n"
        "```javascript\n"
        "const { test, expect } = require('@playwright/test');\n"
        "test('login', async ({ page }) => { await page.locator('#new').click(); });\n"
        "```"
    )
    code = extract_code_from_response(response)
    assert code is not None
    assert "#new" in code


def test_parse_error_context_splits_sections():
    content = (
        "# Error details\n\n```\nError: locator.click: Test timeout of 30000ms exceeded.\n"
        "Call log:\n  - waiting for locator('text=\\'Sign In\\'')\n\n```\n\n"
        '# Page snapshot\n\n```yaml\n- button "Sign in" [ref=e3]\n```\n\n'
        "# Test source\n\n```ts\nawait expect(page.locator('#x')).toHaveText('y');\n```\n"
    )
    call_log, page_snapshot = parse_error_context(content)
    assert "waiting for locator" in call_log
    assert 'button "Sign in"' in page_snapshot
    # Test source must never leak into either section — expect() lines in
    # healthy code would misclassify the failure as an assertion error.
    assert "toHaveText" not in call_log + page_snapshot


def test_extract_failed_selector_from_escaped_call_log():
    call_log = "  - waiting for locator('text=\\'Sign In\\'')"
    assert extract_failed_selector("Test timeout of 30000ms exceeded.", call_log) == "text='Sign In'"


def test_tier1_case_corrects_text_selector():
    """The e2e demo scenario: button copy changed 'Sign In' -> 'Sign in'."""
    failure = TestFailure(
        failure_type=FailureType.LOCATOR_TIMEOUT,
        error_message="Test timeout of 30000ms exceeded.",
        failed_selector="text='Sign In'",
        test_code="await page.locator(\"text='Sign In'\").click();",
        page_html='- button "Sign in" [ref=e3]',
    )
    result = asyncio.run(tier1_healer.heal(failure))
    assert result.success
    assert "text='Sign in'" in result.healed_code


def test_deduplicate_code_removes_duplicate_test_block():
    code = (
        "test('a', async ({ page }) => {\n  await page.goto('/');\n});\n"
        "test('a', async ({ page }) => {\n  await page.goto('/');\n});"
    )
    deduped = deduplicate_code(code)
    assert deduped.count("test('a'") == 1
    assert deduped.rstrip().endswith("});")


def test_llm_client_prefers_subscription_cli(monkeypatch):
    from ninelives.llm import client as client_mod

    monkeypatch.delenv("NINELIVES_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(client_mod, "detect_agent_clis", lambda: ["claude-code"])
    assert client_mod.LLMClient().provider == "claude-code"

    # No CLI installed -> fall back to the API key.
    monkeypatch.setattr(client_mod, "detect_agent_clis", lambda: [])
    assert client_mod.LLMClient().provider == "anthropic"


def test_llm_client_env_override_wins(monkeypatch):
    from ninelives.llm import client as client_mod

    monkeypatch.setenv("NINELIVES_PROVIDER", "openai")
    monkeypatch.setattr(client_mod, "detect_agent_clis", lambda: ["claude-code"])
    assert client_mod.LLMClient().provider == "openai"


def test_agent_cli_unknown_provider_raises():
    import pytest

    from ninelives.llm.agent_cli import call_agent_cli

    with pytest.raises(RuntimeError, match="Unknown agent CLI provider"):
        call_agent_cli("not-a-provider", "sys", "user")


def test_agent_cli_prompt_dispatch_stdin_vs_arg(monkeypatch):
    """stdin providers get the prompt on stdin (never in argv); the arg provider
    gets it as the last argv element with stdin closed (no non-TTY EOF hang)."""
    import subprocess as sp

    from ninelives.llm import agent_cli

    seen = {}

    class FakeProc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(agent_cli.shutil, "which", lambda b: f"/usr/bin/{b}")
    monkeypatch.setattr(agent_cli.tempfile, "mkdtemp", lambda **k: "/tmp/x")
    monkeypatch.setattr(agent_cli.subprocess, "run", lambda argv, **kw: (seen.update(argv=argv, kw=kw), FakeProc())[1])

    agent_cli.call_agent_cli("codex", "SYS", "USER")  # stdin provider
    assert seen["kw"].get("input") == "SYS\n\nUSER"
    assert "SYS\n\nUSER" not in seen["argv"] and seen["argv"][-1] == "-"

    agent_cli.call_agent_cli("opencode", "SYS", "USER")  # arg provider
    assert seen["argv"][-1] == "SYS\n\nUSER"
    assert seen["kw"].get("stdin") == sp.DEVNULL and "input" not in seen["kw"]


def test_render_markdown_report():
    from ninelives.report.github import SpecOutcome, render_markdown

    outcomes = [
        SpecOutcome(spec="login.spec.ts", status="healed", detail="Replaced selector", diff="-a\n+b"),
        SpecOutcome(spec="cart.spec.ts", status="passed", detail="1.2s"),
        SpecOutcome(spec="checkout.spec.ts", status="failed", detail="Timeout | strict"),
    ]
    body = render_markdown(outcomes, "heal")
    assert "1 failing, 1 healed" in body
    assert "| `login.spec.ts` | 🐾 healed |" in body
    assert "Timeout \\| strict" in body  # pipes escaped for the table
    assert "```diff" in body
    assert "9lives.run" in body  # the footer IS the growth loop


def test_write_github_reports(tmp_path, monkeypatch):
    from ninelives.report.github import COMMENT_BODY_FILENAME, SpecOutcome, write_github_reports

    summary = tmp_path / "summary.md"
    output = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.chdir(tmp_path)

    write_github_reports([SpecOutcome(spec="a.spec.ts", status="healed", detail="fixed")], "heal")

    assert "9lives heal report" in summary.read_text()
    assert "status=healed" in output.read_text()
    assert "healed=1" in output.read_text()
    assert (tmp_path / COMMENT_BODY_FILENAME).exists()


def test_write_github_reports_noop_outside_ci(tmp_path, monkeypatch):
    from ninelives.report.github import COMMENT_BODY_FILENAME, SpecOutcome, write_github_reports

    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.chdir(tmp_path)
    write_github_reports([SpecOutcome(spec="a.spec.ts", status="passed")], "run")
    assert not (tmp_path / COMMENT_BODY_FILENAME).exists()


def test_replace_selector_handles_regex_metachars_in_replacement():
    """A new selector containing a backslash or \\1 (e.g. a page showing a
    Windows path) must be inserted literally, not crash re.sub."""
    out = tier1_healer._replace_selector('page.locator("#a").click();', "#a", r"#c\1d")
    assert r"#c\1d" in out


def test_render_markdown_fences_diff_containing_backticks():
    from ninelives.report.github import SpecOutcome, render_markdown

    diff = "-const x = `a`\n+const x = ```b```"  # 3-backtick run inside the diff
    body = render_markdown([SpecOutcome(spec="s.spec.ts", status="healed", diff=diff)], "heal")
    assert "````diff" in body  # fence widened past the inner run so it can't break out
    assert "```b```" in body


def test_llm_client_available_falls_back_to_key_when_cli_absent(monkeypatch):
    from ninelives.llm import client as client_mod

    monkeypatch.setenv("NINELIVES_PROVIDER", "claude-code")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(client_mod, "detect_agent_clis", lambda: [])
    c = client_mod.LLMClient()
    assert c.is_subscription
    assert c.available  # an API key makes it usable even if the CLI isn't there


def test_llm_client_subscription_call_falls_back_to_api_key(monkeypatch):
    from ninelives.llm import client as client_mod

    monkeypatch.setenv("NINELIVES_PROVIDER", "claude-code")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(client_mod, "detect_agent_clis", lambda: ["claude-code"])

    def not_logged_in(*a, **k):
        raise RuntimeError("not logged in")

    monkeypatch.setattr(client_mod, "call_agent_cli", not_logged_in)
    c = client_mod.LLMClient()
    monkeypatch.setattr(c, "_call_anthropic", lambda *a, **k: "HEALED")
    assert c.call(system="s", user="u") == "HEALED"
    assert c.provider == "anthropic"  # switched to the key on fallback


def test_heal_working_copy_is_sibling_in_user_project(tmp_path, monkeypatch):
    """In a real Playwright project the working copy must stay next to the spec
    (config/fixtures resolve) and be cleaned up afterward."""
    from ninelives import cli
    from ninelives.runner.execute import RunResult

    spec = tmp_path / "login.spec.js"
    spec.write_text("await page.locator('#x').click();\n")

    seen = {}

    def fake_run_spec(working_spec):
        seen["path"] = Path(working_spec)
        seen["existed"] = Path(working_spec).exists()
        return RunResult(passed=True, exit_code=0)

    monkeypatch.setattr(cli, "find_user_project", lambda p: tmp_path)
    monkeypatch.setattr(cli, "run_spec", fake_run_spec)

    outcome = cli.heal_one(spec, auto_apply=True)
    assert outcome.status == "passed"
    assert seen["path"].parent == spec.resolve().parent
    assert seen["path"].name != spec.name
    assert seen["existed"]
    assert not seen["path"].exists()  # cleaned up


def test_heal_verifies_final_attempt_when_max_iterations_one(tmp_path, monkeypatch):
    """--max-iterations 1 must be able to report a heal: the fix produced on the
    last pass has to be re-run, not left unverified as a false 'still failing'."""
    from ninelives import cli
    from ninelives.healing.strategy import FailureType, HealingResult, HealingTier
    from ninelives.runner.execute import RunResult, TestError

    spec = tmp_path / "login.spec.js"
    spec.write_text("await page.locator('#old').click();\n")

    runs = []

    def fake_run_spec(working_spec):
        runs.append(1)
        if len(runs) == 1:
            return RunResult(passed=False, exit_code=1, errors=[TestError(title="t", message="locator not found")])
        return RunResult(passed=True, exit_code=0)

    async def fake_heal(failure):
        return HealingResult(
            tier=HealingTier.TIER1_AUTO,
            success=True,
            healed_code="await page.locator('#new').click();\n",
            changes_made=["swap selector"],
            confidence=0.85,
        )

    monkeypatch.setattr(cli, "find_user_project", lambda p: None)
    monkeypatch.setattr(cli, "run_spec", fake_run_spec)
    monkeypatch.setattr(cli.healing_strategy_selector, "classify_failure", lambda *a, **k: FailureType.LOCATOR_NOT_FOUND)
    monkeypatch.setattr(cli.healing_strategy_selector, "select_strategy", lambda f: HealingTier.TIER1_AUTO)
    monkeypatch.setattr(cli.tier1_healer, "heal", fake_heal)

    outcome = cli.heal_one(spec, auto_apply=True, max_iterations=1)
    assert outcome.status == "healed"
    assert len(runs) == 2  # initial failing run + final verification run
    assert spec.read_text() == "await page.locator('#new').click();\n"


def test_preflight_bare_spec_ok(tmp_path):
    # No package.json anywhere → 9lives will scaffold; preflight must not raise.
    spec = tmp_path / "login.spec.js"
    spec.write_text("test('x', async () => {});\n")
    ensure_project_ready(spec)


def test_preflight_real_playwright_project_ok(tmp_path):
    (tmp_path / "package.json").write_text('{"devDependencies": {"@playwright/test": "1.61.1"}}')
    spec = tmp_path / "login.spec.js"
    spec.write_text("test('x', async () => {});\n")
    ensure_project_ready(spec)  # real project → no raise


def test_preflight_project_missing_playwright_raises(tmp_path):
    # A real Node project that simply hasn't installed @playwright/test → clear error,
    # NOT a silent detached scaffold that heal would then try to "fix".
    (tmp_path / "package.json").write_text('{"dependencies": {"react": "18.0.0"}}')
    spec = tmp_path / "login.spec.js"
    spec.write_text("test('x', async () => {});\n")
    raised = False
    try:
        ensure_project_ready(spec)
    except RunnerError as exc:
        raised = True
        assert "@playwright/test" in str(exc)
    assert raised, "expected RunnerError when the enclosing project lacks @playwright/test"
