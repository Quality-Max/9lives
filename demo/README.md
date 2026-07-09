# 🐾 9lives demo — watch a test heal itself

A coding agent renamed a button from **“Sign In”** to **“Sign in”**, and the
Playwright test went red. `9l heal` reads the live page, finds the element under
its new label, patches the spec, re-runs it green, and shows you the diff — all
**offline** (Tier 1, no API key).

![9lives healing a broken selector](heal.gif)

## Run it yourself (one command)

```bash
pip install 9lives            # or: uvx --from 9lives 9l ...
cd demo && ./heal.sh
```

`heal.sh` serves the tiny local page in [`site/`](site/index.html), then runs
`9l heal login.spec.js`. The spec ships **broken** on purpose:

```js
await page.locator("text='Sign In'").click();   // page now says "Sign in"
```

You'll watch it become `text='Sign in'` and pass. `git checkout -- login.spec.js`
resets it to broken so you can run the demo again.

## Regenerate the GIF

```bash
./record.sh        # asciinema + agg → heal.gif  (deps: asciinema, agg, 9l, node)
```
