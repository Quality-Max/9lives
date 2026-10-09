# Contributing to 9lives 🐾

Every issue gets triaged, every PR gets a review — usually same-day. Contributing should feel effortless; if it doesn't, that's a bug in our process, file it.

The Python CLI is in maintenance mode. Send new CLI features and framework development to [9lives-runner](https://github.com/Quality-Max/9lives-runner). This repository accepts security, correctness, compatibility, and migration fixes for existing Python users. See the [transition policy and retirement gates](docs/MIGRATING_TO_GO.md).

## Dev setup

```bash
git clone https://github.com/Quality-Max/9lives && cd 9lives
uv sync --extra all          # or: pip install -e '.[all]'
uv run pytest                # unit tests — pure, no network, fast
uv run ruff check src tests && uv run ruff format --check src tests
```

Node ≥ 18 is needed only for running actual Playwright specs (`9lives run` / `9lives heal`), not for the unit tests.

## What we merge fast

- Fixes to existing healing strategies that preserve test intent, with regressions
- Compatibility fixes for supported agent CLI adapters in `src/ninelives/llm/agent_cli.py`
- Failure-classification patterns for error messages we misread (attach the real Playwright output)
- Docs, examples, install-path fixes for platforms we haven't met

## Ground rules

- **Tier 1 stays offline.** No network calls in `healing/tier1.py` or `healing/strategy.py`, ever.
- **No telemetry, no accounts, no phone-home.** PRs adding any will be closed with love.
- **Diff-first.** Anything that modifies a user's file must show a diff and respect `--yes`.
- Tests for behavior changes; `ruff check` + `ruff format` clean.

## Releasing (maintainers)

Tag `vX.Y.Z` → CI publishes to PyPI and cuts a GitHub release. Keep the `v1` major tag on the latest compatible commit for `uses: quality-max/9lives/action@v1`.

Maintenance releases must preserve the Python entry points, MCP protocol, and existing Action/hook behavior. Do not remove the `9l` alias, automatically download or invoke Go, or redirect Python commands to another engine in a maintenance release. Announce any later breaking transition separately. Retain the pinned Python sources used by the Go runner's differential compatibility tests.
