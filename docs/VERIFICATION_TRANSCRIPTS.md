# 9lives v0.1 — verification transcripts

Verbatim transcripts from the development session (2026-07-04) in which every
headline claim of the prototype was exercised end-to-end. Environment:
Claude Code remote container, Linux, Node v22.22.2, preinstalled chromium
(rev 1194) via `NINELIVES_CHROMIUM_PATH=/opt/pw-browsers/chromium`,
**no `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` set at any point**.

---

## 1. `9l doctor` — environment + provider detection

```
$ 9l doctor
 ✓ node     v22.22.2
 ✓ npx
 ✓ agent    claude-code (subscription — used for Tier 2)
 ✓ LLM key  not needed — using your claude-code subscription

🐾 ready
```

Before subscription mode shipped, the same command reported:

```
 ✓ node     v22.22.2
 ✓ npx
 ✗ LLM key  none — Tier 1 offline healing still works; set ANTHROPIC_API_KEY or OPENAI_API_KEY for Tier 2

🐾 ready
```

## 2. Tier 1 — offline heal, zero LLM, zero network

Fixture: a page whose button copy changed from `Sign In` to `Sign in`
(`<button id="auth-submit">Sign in</button>`); the spec still used the old
text selector.

```
$ 9l heal --yes login.spec.js
🐾 run 1/3: login.spec.js …
  failure: locator_not_found (selector: text='Sign In') → tier1_auto
  tier1_auto: Replaced selector 'text='Sign In'' with 'text='Sign in'' (confidence 85%)
🐾 run 2/3: login.spec.js …

🐾 healed! (+1 / -1)

--- a/login.spec.js
+++ b/login.spec.js
@@ -1,7 +1,7 @@
 const { test, expect } = require('@playwright/test');

 test('user can sign in', async ({ page }) => {
   await page.goto('file:///…/demo/page.html');
-  await page.locator("text='Sign In'").click();
+  await page.locator("text='Sign in'").click();
   await expect(page.locator('#auth-submit')).toHaveText('Welcome!');
 });

🐾 applied. Your test came back to life.
```

Confirmation the healed spec passes:

```
$ 9l run login.spec.js
🐾 running …/demo/login.spec.js …
🐾 PASSED in 1.5s
```

The Tier 1 heal used only the failure-time page snapshot from Playwright's
`error-context.md` — no LLM call, no API key, no network.

## 3. Tier 2 — subscription mode (`claude -p`), structural break

Fixture: a spec clicking `#signup-submit-btn`, an id that never existed —
the real button is `<button>Continue with email</button>` next to an email
input. Tier 1 cannot fix this offline (the aria snapshot carries no ids), so
it escalates to Tier 2, which ran through the logged-in **Claude Code CLI
subscription** — no API key configured.

```
$ 9l heal --yes signup.spec.js
🐾 run 1/3: signup.spec.js …
  failure: locator_not_found (selector: #signup-submit-btn) → tier2_ai_suggest
  tier2_ai_suggest: Replaced the invalid `#signup-submit-btn` id selector with a
    role/text-based locator matching the actual button rendered on the page:
    `page.getByRole('button', { name: 'Continue with email' })`. (confidence 70%)
  tier2_ai_suggest: … I've added a `fill` step for the email field as a minimal,
    reasonable inference from the visible textbox, since clicking "Continue" with
    an empty email field would likely not progress the flow. (confidence 70%)
🐾 run 2/3: signup.spec.js …

🐾 healed! (+3 / -2)

--- a/signup.spec.js
+++ b/signup.spec.js
@@ -1,7 +1,8 @@
 const { test, expect } = require('@playwright/test');

 test('user can start signup', async ({ page }) => {
   await page.goto('file:///…/demo2/page.html');
-  await page.locator('#signup-submit-btn').click();
+  await page.getByRole('textbox', { name: 'Email address' }).fill('test@example.com');
+  await page.getByRole('button', { name: 'Continue with email' }).click();
   await expect(page.locator('form button')).toHaveText('Welcome!');
 });

🐾 applied. Your test came back to life.
```

Note the heal is better than a selector patch: it adopted `getByRole`
(Playwright best practice) and inferred the required email-fill step.

## 4. CI simulation — the GitHub Action contract

Same Tier 1 fixture, re-broken, run exactly as `action/action.yml` runs it
(with `GITHUB_STEP_SUMMARY` and `GITHUB_OUTPUT` pointing at files):

```
$ GITHUB_STEP_SUMMARY=… GITHUB_OUTPUT=… 9l heal --yes login.spec.js
…
🐾 applied. Your test came back to life.

=== GITHUB_OUTPUT ===
status=healed
healed=1
failed=0

=== PR comment body (.9lives-report.md) ===
## 🐾 9lives heal report — 🐾 1 test(s) came back to life

| spec | status | detail |
|---|---|---|
| `login.spec.js` | 🐾 healed | Replaced selector 'text='Sign In'' with 'text='Sign in'' |

<details><summary>diff — login.spec.js</summary>
… (unified diff) …
</details>

---
🐾 checked by [9lives](https://9lives.run) — `curl -sL 9l.run | sh`
```

## 5. Unit tests + lint

```
$ pytest tests/ -q
18 passed

$ ruff check src/ tests/
All checks passed!
$ ruff format --check src/ tests/
15 files already formatted
```

## Fixes discovered *by* these runs

Running the real loop surfaced (and fixed, with regression tests):

1. Playwright's call logs escape nested quotes (`locator('text=\'Sign In\'')`)
   — selector extraction now handles backslash-escaped quotes.
2. `error-context.md` embeds the test source; feeding the whole file to the
   classifier misread healthy `expect()` lines as assertion failures — the
   file is now split into call-log / page-snapshot sections.
3. Tier 1's text healing returned the *original* casing (a no-op heal) — it
   now adopts the live page casing and rejects identical-selector "heals".
4. Tier 1's blind selector transforms could claim success repeatedly and burn
   all heal iterations before Tier 2 ran — Tier 1 now gets one shot per
   session, then escalates.
5. ANSI color codes polluted JSON-report error messages — stripped.
