# Contributing to 9lives 🐾

Every issue gets triaged, every PR gets a review — usually same-day. Contributing should feel effortless; if it doesn't, that's a bug in our process, file it.

## Dev setup

```bash
git clone https://github.com/Quality-Max/9lives && cd 9lives
uv sync --extra all          # or: pip install -e '.[all]'
uv run pytest                # unit tests — pure, no network, fast
uv run ruff check src tests && uv run ruff format --check src tests
```

Node ≥ 18 is needed only for running actual Playwright specs (`9l run` / `9l heal`), not for the unit tests.

## What we merge fast

- New Tier 1 healing strategies (offline selector recovery) with tests
- New agent CLI adapters in `src/ninelives/llm/agent_cli.py` — one dict entry + a test
- Failure-classification patterns for error messages we misread (attach the real Playwright output)
- Docs, examples, install-path fixes for platforms we haven't met

## Ground rules

- **Tier 1 stays offline.** No network calls in `healing/tier1.py` or `healing/strategy.py`, ever.
- **No telemetry, no accounts, no phone-home.** PRs adding any will be closed with love.
- **Diff-first.** Anything that modifies a user's file must show a diff and respect `--yes`.
- Tests for behavior changes; `ruff check` + `ruff format` clean.

## Releasing (maintainers)

Tag `vX.Y.Z` → CI publishes to PyPI and cuts a GitHub release. Keep the `v1` major tag on the latest compatible commit for `uses: quality-max/9lives/action@v1`.
