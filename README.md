# 🐾 9lives

**Your tests have nine lives.** Self-healing QA for the coding-agent era, by [QualityMax](https://qualitymax.io).

![9lives healing a broken Playwright selector — offline, in seconds](demo/heal.gif)

> A coding agent renamed a button, the test went red, `9l heal` read the live page, fixed the locator, re-ran it green, and showed the diff — no API key. [**Run the demo yourself →**](demo/)

Your coding agent shipped a change and your Playwright test went red? Don't rewrite it — resurrect it:

```bash
9l heal login.spec.ts
```

`9l` runs the test, classifies the failure, and heals it in tiers:

1. **Tier 1 — offline, free, instant.** Selector drifted? 9lives finds the element again from the failure-time page snapshot (text, testid, id, class, aria-label) and rewrites the locator. No LLM, no network, no account.
2. **Tier 2 — the subscription you already pay for.** Structural change? 9lives shells out to your installed coding-agent CLI — **Claude Code (`claude -p`), Codex (`codex exec`), or OpenCode (`opencode run`)** — so your existing subscription does the thinking. No API key to mint, nothing to configure: if the CLI is logged in, healing works. (Prefer raw API? `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` work too.)
3. **Always a diff, never a surprise.** Healed code is shown as a unified diff and applied only when you approve (or `--yes` in CI).

**Won't hide your bugs.** A failing *assertion* means the app's behavior changed — not that a selector moved. 9lives refuses to rewrite assertions to force a green (that's how naive auto-healers mask regressions) and flags it as a possible real bug instead. Opt in with `NINELIVES_HEAL_ASSERTIONS=1` if you really want it to propose an assertion update.

## Install

```bash
curl -sL 9lives.run | sh
pip install 9lives          # or: uv tool install 9lives
```

Requires Node.js ≥ 18 (Playwright itself runs on Node). Check your setup with `9l doctor`.

## Commands

```bash
9l run <spec>         # run a spec locally; screenshots/videos/traces in .9lives/
9l heal <spec>        # run → heal → re-run → diff → apply on confirm
9l heal <spec> --yes  # CI mode: apply automatically, exit code tells the story
9l watch [dir]        # heal on save — polls specs, heals whatever changes
9l report             # brittle-selector report from your local heal history
9l mcp                # serve heal_test/run_test as MCP tools for coding agents
9l doctor             # environment check
```

Works inside an existing Playwright project (uses your `package.json`) or on a bare `.spec.ts` file (scaffolds an ephemeral project automatically). All commands accept multiple specs/globs.

## Cypress & Selenium too

The heal verb is framework-agnostic. `9l heal` auto-detects the framework per spec — `.cy.js`/`.cy.ts` (or a package.json depending on cypress) runs through **Cypress**, `.py` specs run through **Selenium via your own pytest**, everything else is Playwright. Force it with `--framework cypress|selenium|playwright`.

```bash
9l heal cypress/e2e/login.cy.js     # runs `npx cypress run` in your project
9l heal tests/test_checkout.py      # runs your pytest + selenium
```

Same loop everywhere: classify → Tier 1 offline selector repair → Tier 2 via your subscription → re-run → diff → approve. Cypress's `Expected to find element: \`#x\`` and Selenium's `NoSuchElementException` payloads both carry the failing selector, and both are correctly treated as *selector drift* — never as assertion failures (Cypress wraps locator misses in `AssertionError`; 9lives sees through that so the behavior-vs-drift guard doesn't misfire). 9lives never scaffolds a Cypress project or a Python env — those specs run against your own install.

## For coding agents: `9l mcp`

Your agent wrote code, a test went red — let it heal the test **in-loop** instead of waiting for CI. `9l mcp` speaks MCP over stdio (zero extra dependencies) and exposes two tools: `heal_test` (run → heal → verify → return the diff; `apply: true` writes it in place, otherwise a `.healed` copy is saved for review) and `run_test`.

```bash
# Claude Code
claude mcp add 9lives -- 9l mcp
# or without installing first:
claude mcp add 9lives -- uvx --from 9lives 9l mcp
```

```json
// Cursor (.cursor/mcp.json) / Codex — any MCP host with stdio servers
{ "mcpServers": { "9lives": { "command": "9l", "args": ["mcp"] } } }
```

The behavior-vs-drift guard applies to agents too: a failing assertion comes back as `needs-human`, with an explicit note that forcing it green would mask a real bug. `heal_test` only accepts existing test files under the directory `9l mcp` was started in (`NINELIVES_MCP_UNRESTRICTED=1` lifts this), since healing a spec ultimately executes it.

Healing is half the loop — the spec has to come from somewhere. 9lives' sibling MCP server, [qmax-mcp](https://github.com/Quality-Max/qmax-mcp) (`npx -y @qualitymax/qmax-mcp`, MIT), covers the other half: scan a page for defects, inspect it for stability-ranked locators and a testability score, generate a Playwright repro, and run it. Same rules — local, free, no account. A spec born on qmax-mcp's stability-ranked locators is exactly the kind 9lives can keep alive when it drifts.

## Heal on save & pre-commit

`9l watch` makes healing part of the edit-save loop: it polls your specs (no OS-specific watchers, works everywhere) and runs the heal loop on whatever changed. `--yes` applies automatically.

```bash
9l watch tests/ --yes
```

As a [pre-commit](https://pre-commit.com) hook — heal (or just run) changed specs before they ever reach CI:

```yaml
repos:
  - repo: https://github.com/Quality-Max/9lives
    rev: v0.2.0
    hooks:
      - id: 9lives-heal   # heals drifted selectors in place; assertion failures still block
      # - id: 9lives-run  # strict variant: run only, never modify
```

## Which selectors are rotting? `9l report`

Every heal appends a line to `.9lives/history.jsonl` next to the spec — locally, never uploaded. `9l report` aggregates that history into a brittle-selector report: which selectors keep breaking, which anchor (testid/id/text/class) keeps re-finding them, and what to pin instead.

```bash
9l report            # terminal table, worst selectors first
9l report --md brittle-selectors.md
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
- **Your runner:** everything executes on your machine or your CI. Nothing leaves it, nothing phones home.
- **No account.** Ever, for anything in this tool.

## Security & trust boundary

Tier 1 healing is fully offline and never sends anything anywhere.

Tier 2 builds its prompt from the failing test plus the **page snapshot captured at failure**. If you heal tests against a site you don't control, that page content becomes model input. In *subscription mode* it is handed to your local coding-agent CLI (`claude` / `codex` / `opencode`), which can run tools — so a hostile page could attempt prompt injection against your agent. 9lives runs the CLI in an empty scratch directory to limit blast radius, but if you heal against untrusted targets, force plain API mode (no agent tools) with:

```
NINELIVES_PROVIDER=anthropic   # or openai
```

## Roadmap

- `9l check` — map your git diff to affected user flows, run/generate targeted tests: *"did my agent break anything?"*
- `9lives-action` — GitHub Action that posts the QA report on PRs, healed commits included
- `9l gen <url>` — crawl a live app and generate a starter test suite

## Status

**v0.1 prototype** — built by [QualityMax](https://qualitymax.io) for local, BYO self-healing Playwright workflows. MIT licensed.
