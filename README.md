# 🐾 9lives

[Go runner website](https://quality-max.github.io/9lives-runner/) · [Migration guide](docs/MIGRATING_TO_GO.md) · [Standalone tools](https://docs.qualitymax.io/free-and-open-source/)

**Status: Python CLI in maintenance mode.** New Playwright projects should use the [9lives Go runner](https://github.com/Quality-Max/9lives-runner). New CLI features belong there; this package continues to receive security, correctness, and compatibility fixes for existing workflows. There is no Python removal date yet.

Read the [migration guide](docs/MIGRATING_TO_GO.md) for installation, command differences, and workflows that still need Python. Both packages provide `9l`; use `9lives` or `python -m ninelives.cli` to select Python explicitly.

## Recommended: Go runner for Playwright

Install the Go binary on macOS or Linux (amd64/arm64), without needing Go or Python:

```bash
curl -fsSL https://9lives.run/install.sh | sh
export PATH="$HOME/.local/share/9lives-runner/bin:$PATH"
9l --version
9l plan tests/
9l run tests/ --timeout 5m --format json
```

The installer uses a pinned, checksum-verified release and installs into a separate Go directory. `curl -fsSL https://9lives.run | sh` selects the same installer. Override the release or destination explicitly with `NINELIVES_VERSION` or `NINELIVES_INSTALL_DIR`; see the [migration guide](docs/MIGRATING_TO_GO.md). It does not install the SDK, project dependencies, or browsers.

Alternatively, download a [prebuilt release](https://github.com/Quality-Max/9lives-runner/releases), or with Go 1.25.13 or newer:

```bash
go install github.com/Quality-Max/9lives-runner/cmd/9l@v0.1.1
# Add your Go binary directory to PATH, then confirm which CLI you selected:
9l --version
9l plan tests/
9l run tests/ --timeout 5m --format json
```

Go requires an existing Playwright project with locally installed tooling and browsers. It provides planning, bounded execution, cancellation, and validated receipts. The optional SDK adds steps and bounded goals; see the [runner documentation](https://github.com/Quality-Max/9lives-runner/blob/main/docs/README.md). Native healing is experimental; Go's `9l heal` still delegates to this Python package.

## Existing Python workflows

The remainder of this README describes the Python package. Hosted QualityMax healing is a separate workflow. Review repair diffs and completed test results before accepting changes.

**Your tests have nine lives.** Self-healing QA for the coding-agent era, by [QualityMax](https://qualitymax.io).

![9lives healing a broken Playwright selector — offline, in seconds](demo/heal.gif)

> Python compatibility demo: a coding agent renamed a button, the test went red, `9lives heal` read the live page, fixed the locator, re-ran it green, and showed the diff — no API key. [**Run the demo yourself →**](demo/)

Your coding agent shipped a change and your Playwright test went red? Don't rewrite it — resurrect it:

```bash
9lives heal login.spec.ts
```

The Python CLI runs the test, classifies the failure, and heals it in tiers:

1. **Tier 1 — offline, free, instant.** Selector drifted? 9lives finds the element again from the failure-time page snapshot (text, testid, id, class, aria-label) and rewrites the locator. No LLM, no network, no account.
2. **Tier 2 — the subscription you already pay for.** Structural change? 9lives shells out to your installed coding-agent CLI — **Claude Code (`claude -p`), Codex (`codex exec`), or OpenCode (`opencode run`)** — so your existing subscription does the thinking. No API key to mint, nothing to configure: if the CLI is logged in, healing works. (Prefer raw API? `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` work too.)
3. **Always a diff, never a surprise.** Healed code is shown as a unified diff and applied only when you approve (or `--yes` in CI).

**Won't hide your bugs.** A failing *assertion* means the app's behavior changed — not that a selector moved. 9lives refuses to rewrite assertions to force a green (that's how naive auto-healers mask regressions) and flags it as a possible real bug instead. Opt in with `NINELIVES_HEAL_ASSERTIONS=1` if you really want it to propose an assertion update.

## Install Python for compatibility

```bash
pip install 9lives          # or: uv tool install 9lives
9lives --version           # Python, even when the Go runner is also installed
```

Requires Node.js ≥ 18 (Playwright itself runs on Node). Check your Python setup with `9lives doctor`. The website and shell installer now recommend and install Go; use `pip` or `uv` explicitly when you need Python compatibility.

## Commands

```bash
9lives run <spec>         # run a spec locally; screenshots/videos/traces in .9lives/
9lives heal <spec>        # run → heal → re-run → diff → apply on confirm
9lives heal <spec> --yes  # CI mode: apply automatically, exit code tells the story
9lives heal <spec> --run-timeout 900   # one spec run may take up to 15 min (default 300s)
9lives watch [dir]        # heal on save — polls specs, heals whatever changes
9lives report            # brittle-selector report from your local heal history
9lives mcp               # serve heal_test/run_test as MCP tools for coding agents
9lives doctor            # environment check
```

Works inside an existing Playwright project (uses your `package.json`) or on a bare `.spec.ts` file (scaffolds an ephemeral project automatically). All commands accept multiple specs/globs.

One spec run gets 300 seconds by default. Suites that legitimately take longer can raise it with `--run-timeout <seconds>` on `run`/`heal`/`watch`, or `NINELIVES_RUN_TIMEOUT=<seconds>` in the environment (the MCP tools take `run_timeout` too). When the budget is exceeded, 9lives stops with a clear error and changes nothing — a heal that never observed a test result never emits a diff.

## Cypress & Selenium too

Python's `9lives heal` auto-detects the framework per spec — `.cy.js`/`.cy.ts` (or a package.json depending on cypress) runs through **Cypress**, `.py` specs run through **Selenium via your own pytest**, everything else is Playwright. Force it with `--framework cypress|selenium|playwright`. Go execution currently supports Playwright only.

```bash
9lives heal cypress/e2e/login.cy.js  # runs `npx cypress run` in your project
9lives heal tests/test_checkout.py  # runs your pytest + selenium
```

Same loop everywhere: classify → Tier 1 offline selector repair → Tier 2 via your subscription → re-run → diff → approve. Cypress's `Expected to find element: \`#x\`` and Selenium's `NoSuchElementException` payloads both carry the failing selector, and both are correctly treated as *selector drift* — never as assertion failures (Cypress wraps locator misses in `AssertionError`; 9lives sees through that so the behavior-vs-drift guard doesn't misfire). 9lives never scaffolds a Cypress project or a Python env — those specs run against your own install.

## For coding agents: Python `9lives mcp`

Your agent wrote code, a test went red — let it heal the test **in-loop** instead of waiting for CI. Python's `9lives mcp` speaks MCP over stdio (zero extra dependencies) and exposes two tools: `heal_test` (run → heal → verify → return the diff; `apply: true` writes it in place, otherwise a `.healed` copy is saved for review) and `run_test`.

```bash
# Claude Code
claude mcp add 9lives -- 9lives mcp
# or without installing first:
claude mcp add 9lives -- uvx --from 9lives 9lives mcp
```

```json
// Cursor (.cursor/mcp.json) / Codex — any MCP host with stdio servers
{ "mcpServers": { "9lives": { "command": "9lives", "args": ["mcp"] } } }
```

The behavior-vs-drift guard applies to agents too: a failing assertion comes back as `needs-human`, with an explicit note that forcing it green would mask a real bug. `heal_test` only accepts existing test files under the directory `9lives mcp` was started in (`NINELIVES_MCP_UNRESTRICTED=1` lifts this), since healing a spec ultimately executes it.

Healing is half the loop — the spec has to come from somewhere. 9lives' sibling MCP server, [qmax-mcp](https://github.com/Quality-Max/qmax-mcp) (`npx -y @qualitymax/qmax-mcp`, MIT), covers the other half: scan a page for defects, inspect it for stability-ranked locators and a testability score, generate a Playwright repro, and run it. Same rules — local, free, no account. A spec born on qmax-mcp's stability-ranked locators is exactly the kind 9lives can keep alive when it drifts.

## Heal on save & pre-commit

Python's `9lives watch` makes healing part of the edit-save loop: it polls your specs (no OS-specific watchers, works everywhere) and runs the heal loop on whatever changed. `--yes` applies automatically.

```bash
9lives watch tests/ --yes
```

As a [pre-commit](https://pre-commit.com) hook — heal (or just run) changed specs before they ever reach CI:

```yaml
repos:
  - repo: https://github.com/Quality-Max/9lives
    rev: v0.2.1
    hooks:
      - id: 9lives-heal   # heals drifted selectors in place; assertion failures still block
      # - id: 9lives-run  # strict variant: run only, never modify
```

## Which selectors are rotting? Python `9lives report`

Every Python heal appends a line to `.9lives/history.jsonl` next to the spec — locally, never uploaded. `9lives report` aggregates that history into a brittle-selector report: which selectors keep breaking, which anchor (testid/id/text/class) keeps re-finding them, and what to pin instead.

```bash
9lives report            # terminal table, worst selectors first
9lives report --md brittle-selectors.md
```

## In CI: the GitHub Action

```yaml
- uses: quality-max/9lives/action@v1
  with:
    specs: "tests/**/*.spec.ts"
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    commit-healed: "true"
```

Runs on **your** runner, heals with **your** key, posts a 🐾 report comment on the PR, and can commit healed specs straight back to the branch. See [`action/`](action/README.md).

## BYO everything

- **Your subscription:** an installed `claude` / `codex` / `opencode` CLI is auto-detected and used for Tier 2, so the subscription you already use for coding can heal tests too.
- **Or your key:** `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`. Force a choice with `NINELIVES_PROVIDER` (`claude-code`, `codex`, `opencode`, `anthropic`, `openai`) and `NINELIVES_MODEL`.
- **Your runner:** tests execute on your machine or CI. Model-assisted healing sends the required test and page-snapshot inputs to your configured coding agent or provider.
- **No QualityMax account required.** Model-assisted tiers use your provider or coding-agent account and may incur charges.

## Security & trust boundary

Tier 1 healing is fully offline and never sends anything anywhere.

Tier 2 builds its prompt from the failing test plus the **page snapshot captured at failure**. If you heal tests against a site you don't control, that page content becomes model input. In *subscription mode* it is handed to your local coding-agent CLI (`claude` / `codex` / `opencode`), which can run tools — so a hostile page could attempt prompt injection against your agent. 9lives runs the CLI in an empty scratch directory to limit blast radius, but if you heal against untrusted targets, force plain API mode (no agent tools) with:

```
NINELIVES_PROVIDER=anthropic   # or openai
```

## Transition policy

New CLI development belongs in [9lives-runner](https://github.com/Quality-Max/9lives-runner). Python's MCP server, watch/history reports, Cypress/Selenium adapters, standalone-spec scaffolding, GitHub Action, and pre-commit hooks remain available while their migration paths are decided. Retirement requires qualified replacements or a documented discontinuation decision, an announced support window, and migration evidence across at least two stable Go releases. See the [migration guide](docs/MIGRATING_TO_GO.md#retirement-gates).

## Status

**Maintenance-only Python compatibility package** — built by [QualityMax](https://qualitymax.io) for local, BYO self-healing workflows. MIT licensed. The Go runner is a separate Apache-2.0 distribution.
