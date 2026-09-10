"""Unit tests for the lifted healing core (pure, no network)."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ninelives.healing.parse import deduplicate_code, extract_code_from_response, extract_failed_selector
from ninelives.healing.patch import diff_stats, generate_unified_diff
from ninelives.healing.strategy import FailureType, HealingTier, TestFailure, healing_strategy_selector
from ninelives.healing.tier1 import tier1_healer
from ninelives.runner.artifacts import parse_error_context
from ninelives.runner.execute import RunnerError, ensure_project_ready


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
    monkeypatch.setattr(client_mod, "detect_agent_clis", list)
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
    monkeypatch.setattr(client_mod, "detect_agent_clis", list)
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

    from ninelives.runner import execute

    monkeypatch.setattr(cli, "find_user_project", lambda p: tmp_path)
    monkeypatch.setattr(execute, "run_spec", fake_run_spec)  # the playwright adapter routes through here

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

    from ninelives.runner import execute

    monkeypatch.setattr(cli, "find_user_project", lambda p: None)
    monkeypatch.setattr(execute, "run_spec", fake_run_spec)  # the playwright adapter routes through here
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


def test_assertion_failure_is_not_auto_healed():
    # Behavior-vs-drift guard: a failing assertion is a possible real bug, so it
    # goes to a human — never a Tier 2 rewrite that would force the test green.
    failure = TestFailure(
        failure_type=FailureType.ASSERTION_FAILED,
        error_message="Error: expect(received).toBe(expected)\nExpected: 5\nReceived: 4",
    )
    assert healing_strategy_selector.select_strategy(failure) == HealingTier.TIER3_HUMAN


def test_assertion_heal_is_opt_in(monkeypatch):
    failure = TestFailure(
        failure_type=FailureType.ASSERTION_FAILED,
        error_message="Expected: 5 Received: 4",
    )
    monkeypatch.setenv("NINELIVES_HEAL_ASSERTIONS", "1")
    assert healing_strategy_selector.select_strategy(failure) == HealingTier.TIER2_AI_SUGGEST


def test_tier1_records_winning_anchor():
    # Anchor redundancy: the heal reports WHICH anchor re-identified the element.
    failure = TestFailure(
        failure_type=FailureType.LOCATOR_NOT_FOUND,
        error_message="waiting for locator('#login-btn')",
        failed_selector="#login-btn",
        test_code="await page.locator('#login-btn').click();",
        page_html='<button id="login-btn-v2">Sign in</button>',
    )
    result = asyncio.run(tier1_healer.heal(failure))
    assert result.success
    assert result.metadata.get("anchor") == "id"
    assert "re-found via id" in result.changes_made[0].lower()


def test_tier1_prefers_stable_anchor_over_class():
    # A selector carrying both a testid and a class should re-find via the
    # stabler testid, not the fragile class.
    failure = TestFailure(
        failure_type=FailureType.LOCATOR_NOT_FOUND,
        error_message="not found",
        failed_selector="[data-testid='submit'].btn-old",
        test_code="await page.locator(\"[data-testid='submit'].btn-old\").click();",
        page_html='<button data-testid="submit" class="btn-new">Go</button>',
    )
    result = asyncio.run(tier1_healer.heal(failure))
    assert result.success
    assert result.metadata.get("anchor") == "testid"


# ---------- issue #19: run timeout, scratch-file cleanup, Tier 2 scope ----------


def test_run_timeout_default_env_and_flag(monkeypatch):
    from ninelives.runner import execute

    monkeypatch.setattr(execute, "_run_timeout_override", None)
    monkeypatch.delenv(execute.RUN_TIMEOUT_ENV, raising=False)
    assert execute.run_timeout() == execute.RUN_TIMEOUT_SECONDS

    monkeypatch.setenv(execute.RUN_TIMEOUT_ENV, "900")
    assert execute.run_timeout() == 900

    execute.set_run_timeout(1200)  # --run-timeout beats the environment
    assert execute.run_timeout() == 1200
    execute.set_run_timeout(None)
    assert execute.run_timeout() == 900

    with execute.override_run_timeout(42):
        assert execute.run_timeout() == 42
    assert execute.run_timeout() == 900  # scoped override restored


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "1.5"])
def test_run_timeout_rejects_bad_values(monkeypatch, bad):
    from ninelives.runner import execute

    monkeypatch.setattr(execute, "_run_timeout_override", None)
    monkeypatch.setenv(execute.RUN_TIMEOUT_ENV, bad)
    with pytest.raises(RunnerError, match=execute.RUN_TIMEOUT_ENV):
        execute.run_timeout()
    with pytest.raises(RunnerError, match="--run-timeout"):
        execute.set_run_timeout(0)


def test_spec_timeout_is_a_handled_error_not_a_traceback(monkeypatch, tmp_path):
    """A spec that outruns its budget must surface as RunnerError with the
    knob to turn — not as a raw subprocess.TimeoutExpired (issue #19)."""
    import subprocess

    from ninelives.runner import execute

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(execute.subprocess, "run", fake_run)
    monkeypatch.setattr(execute, "_run_timeout_override", None)
    monkeypatch.setenv(execute.RUN_TIMEOUT_ENV, "7")

    with pytest.raises(execute.RunTimeoutError) as info:
        execute.run_test_command(["npx", "playwright", "test", "x.spec.ts"], tmp_path)
    message = str(info.value)
    assert "7s" in message and "--run-timeout" in message and execute.RUN_TIMEOUT_ENV in message
    assert isinstance(info.value, RunnerError)  # main() turns it into `🐾 error:` + exit 2

    with pytest.raises(execute.RunTimeoutError, match="timed out after 5s"):
        execute._run(["/usr/bin/npm", "install"], tmp_path, 5)


def test_cli_run_timeout_flag_reaches_runner(monkeypatch, tmp_path):
    from ninelives import cli
    from ninelives.runner import execute

    monkeypatch.setattr(execute, "_run_timeout_override", None)
    monkeypatch.setattr(cli, "cmd_run", lambda specs, framework: 0)
    assert cli.main(["run", str(tmp_path / "x.spec.ts"), "--run-timeout", "600"]) == 0
    assert execute.run_timeout() == 600

    assert cli.main(["run", str(tmp_path / "x.spec.ts"), "--run-timeout", "0"]) == 2  # handled, not a traceback
    execute.set_run_timeout(None)


def test_bad_run_timeout_env_does_not_block_diagnostic_commands(monkeypatch, tmp_path):
    from ninelives import cli
    from ninelives.runner import execute

    monkeypatch.setattr(execute, "_run_timeout_override", None)
    monkeypatch.setenv(execute.RUN_TIMEOUT_ENV, "abc")
    monkeypatch.setattr(cli, "cmd_doctor", lambda: 0)
    monkeypatch.setattr(cli, "cmd_report", lambda path, md_path: 0)

    assert cli.main(["doctor"]) == 0
    assert cli.main(["report", str(tmp_path)]) == 0
    assert cli.main(["run", str(tmp_path / "x.spec.ts")]) == 2


def test_heal_timeout_leaves_spec_untouched_and_removes_working_copy(tmp_path, monkeypatch):
    """When the run itself cannot complete, heal must emit nothing: no diff,
    no .healed copy, no stray _9lives_heal_* spec in the test directory."""
    from ninelives import cli
    from ninelives.runner import execute

    spec = tmp_path / "login.spec.js"
    original = "await page.locator('#x').click();\n"
    spec.write_text(original)

    def fake_run_spec(working_spec):
        raise execute.RunTimeoutError("spec exceeded the 300s run timeout")

    monkeypatch.setattr(cli, "find_user_project", lambda p: tmp_path)
    monkeypatch.setattr(execute, "run_spec", fake_run_spec)

    with pytest.raises(RunnerError):
        cli.heal_one(spec, auto_apply=True)

    assert spec.read_text() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["login.spec.js"]


def test_heal_sweeps_stale_working_copy_from_killed_process(tmp_path, monkeypatch):
    """SIGKILL never reaches `finally`; the next heal cleans up what it left behind,
    but leaves a copy whose owning process is still alive."""
    from ninelives import cli
    from ninelives.runner import execute
    from ninelives.runner.execute import RunResult

    spec = tmp_path / "login.spec.js"
    spec.write_text("await page.locator('#x').click();\n")
    stale = tmp_path / "_9lives_heal_999999_login.spec.js"
    stale.write_text("// leftover from a killed heal\n")
    live = tmp_path / "_9lives_heal_424242_login.spec.js"
    live.write_text("// concurrent heal still running\n")
    other = tmp_path / "_9lives_heal_999999_other.spec.js"
    other.write_text("// stale copy of a different spec\n")

    monkeypatch.setattr(cli, "_pid_alive", lambda pid: pid == 424242)
    monkeypatch.setattr(cli, "find_user_project", lambda p: tmp_path)
    monkeypatch.setattr(execute, "run_spec", lambda working_spec: RunResult(passed=True, exit_code=0))

    cli.heal_one(spec, auto_apply=True)

    assert not stale.exists()
    assert live.exists()
    assert not other.exists()


def test_heal_sigterm_unwinds_through_cleanup(tmp_path, monkeypatch):
    import os
    import signal

    from ninelives import cli
    from ninelives.runner import execute

    spec = tmp_path / "login.spec.js"
    spec.write_text("await page.locator('#x').click();\n")

    def fake_run_spec(working_spec):
        os.kill(os.getpid(), signal.SIGTERM)  # delivered synchronously to this thread
        raise AssertionError("SIGTERM handler should have raised SystemExit")

    monkeypatch.setattr(cli, "find_user_project", lambda p: tmp_path)
    monkeypatch.setattr(execute, "run_spec", fake_run_spec)
    before = signal.getsignal(signal.SIGTERM)

    with pytest.raises(SystemExit) as info:
        cli.heal_one(spec, auto_apply=True)

    assert info.value.code == 128 + signal.SIGTERM
    assert sorted(p.name for p in tmp_path.iterdir()) == ["login.spec.js"]
    assert signal.getsignal(signal.SIGTERM) == before  # handler restored


def test_comment_changes_are_detected_even_alongside_code_changes():
    from ninelives.healing.patch import comments_changed

    code = "// login flow\nawait page.locator('#old').click();\n"
    assert comments_changed(
        code, "// Login flow — run with: npx playwright test login\n// verified\nawait page.locator('#old').click();\n"
    )
    assert comments_changed(code, "// verified\nawait page.locator('#new').click();\n")
    assert not comments_changed(code, "// login flow\nawait page.locator('#new').click();\n")
    assert not comments_changed(code, code)
    py = "# helper\ndriver.find_element(By.ID, 'old')\n"
    assert comments_changed(py, "# helper (rewritten)\ndriver.find_element(By.ID, 'old')\n")


def test_tier2_rejects_comment_edits_and_keeps_trailing_newline():
    """Reject invented prose whether or not the model also fixes the locator."""
    from ninelives.healing.strategy import FailureType, TestFailure
    from ninelives.healing.tier2 import Tier2AISuggest

    code = "// login flow\nawait page.locator('input[name=\"user\"]').fill('a');\n"
    failure = TestFailure(
        failure_type=FailureType.LOCATOR_NOT_FOUND,
        error_message="locator not found",
        failed_selector='input[name="user"]',
        stack_trace="",
        test_code=code,
        framework="playwright",
    )

    class FakeClient:
        def __init__(self, reply):
            self.reply = reply

        def call(self, **kwargs):
            return self.reply

    prose_only = (
        "REASONING: x\nCHANGES:\n- clarified header\nCODE:\n```javascript\n"
        "// Login flow. Run with `npx playwright test login-flow.spec.ts` (either works, both verified)\n"
        "await page.locator('input[name=\"user\"]').fill('a');\n```"
    )
    result = asyncio.run(Tier2AISuggest(client=FakeClient(prose_only)).suggest(failure))
    assert result.success is False
    assert "comments" in result.metadata["reason"]
    assert result.healed_code is None

    mixed_edit = (
        "REASONING: x\nCHANGES:\n- switch to label and update header\nCODE:\n```javascript\n"
        "// Login flow. Verified against staging; both selectors tested and working.\n"
        "await page.getByLabel('User').fill('a');\n```"
    )
    result = asyncio.run(Tier2AISuggest(client=FakeClient(mixed_edit)).suggest(failure))
    assert result.success is False
    assert "comments" in result.metadata["reason"]
    assert result.healed_code is None

    real_fix = (
        "REASONING: x\nCHANGES:\n- switch to label\nCODE:\n```javascript\n"
        "// login flow\nawait page.getByLabel('User').fill('a');\n```"
    )
    result = asyncio.run(Tier2AISuggest(client=FakeClient(real_fix)).suggest(failure))
    assert result.success is True
    assert result.healed_code.endswith("\n")  # `.strip()` used to drop the file's final newline
    assert result.healed_code == "// login flow\nawait page.getByLabel('User').fill('a');\n"

    prompt = Tier2AISuggest(client=FakeClient(""))._build_prompt(failure)
    assert "verified" in prompt and "Do not edit comments" in prompt


def test_version_is_single_sourced():
    """The build and runtime both read the version from ninelives.__init__."""
    import re

    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    project_section = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", pyproject).group(1)
    hatch_version_section = re.search(r"(?ms)^\[tool\.hatch\.version\]\s*(.*?)(?=^\[|\Z)", pyproject).group(1)

    assert re.search(r'^dynamic\s*=\s*\[\s*"version"\s*\]', project_section, re.MULTILINE)
    assert not re.search(r"^version\s*=", project_section, re.MULTILINE)
    assert re.search(r'^path\s*=\s*"src/ninelives/__init__\.py"', hatch_version_section, re.MULTILINE)


def test_cleanup_restores_default_for_non_python_signal_handler(monkeypatch):
    from ninelives import cli

    calls = []

    def fake_signal(signum, handler):
        calls.append((signum, handler))

    monkeypatch.setattr(cli.signal, "signal", fake_signal)
    supported = [getattr(cli.signal, name, None) for name in ("SIGTERM", "SIGHUP")]
    supported = [signum for signum in supported if signum is not None]

    with cli._cleanup_on_termination():
        pass

    assert [signum for signum, _ in calls[: len(supported)]] == supported
    assert calls[len(supported) :] == [(signum, cli.signal.SIG_DFL) for signum in supported]
