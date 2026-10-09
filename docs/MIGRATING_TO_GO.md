# Migrating from the Python CLI to the Go runner

The [9lives Go runner](https://quality-max.github.io/9lives-runner/) is the primary CLI for new Playwright projects. The Python `9lives` package is in maintenance mode: security, correctness, compatibility, and migration fixes continue; new CLI features belong in the [runner repository](https://github.com/Quality-Max/9lives-runner). Python remains available for existing workflows. There is no removal date yet.

## Install and select the right executable

The distributions are separate. Go ships macOS/Linux binaries for amd64 and arm64; Windows is not a declared runner target. The default website installer now downloads the Go runner, verifies the selected archive against its release's SHA256SUMS, and installs the binary plus LICENSE/NOTICE:

```sh
curl -fsSL https://9lives.run/install.sh | sh
export PATH="$HOME/.local/share/9lives-runner/bin:$PATH"
9l --version
```

The root endpoint (`curl -fsSL https://9lives.run | sh`) serves the same script to non-HTML clients. The default release is pinned to `v0.1.1`; choose another stable release or an absolute destination explicitly:

```sh
curl -fsSL https://9lives.run/install.sh | \
  NINELIVES_VERSION=v0.1.1 NINELIVES_INSTALL_DIR="$HOME/.local/share/9lives-runner/bin" sh
```

The installer prints the PATH command and does not edit shell profiles. Its separate default directory leaves Python's entry points available. If a custom destination already contains a symlink or another CLI called `9l`, installation stops rather than overwriting it. Update any scripts that relied on the old Python installer to use `pip install 9lives` or `uv tool install 9lives` explicitly.

Alternatively, download a pinned [release and verify its checksum](https://github.com/Quality-Max/9lives-runner/blob/main/docs/install.md), or with Go 1.25.13 or newer:

```sh
go install github.com/Quality-Max/9lives-runner/cmd/9l@v0.1.1
"$(go env GOPATH)/bin/9l" --version
```

If you set `GOBIN`, use that directory instead. Use an explicit Go binary path until you have checked `command -v 9l` and `9l --version`: Python also installs a `9l` command, and PATH order decides which one runs. Installing both into the same binary directory can also collide; give the Go binary a separate path during the transition. Do not uninstall Python until its remaining workflows have been accounted for.

Select Python with its separate `9lives` command, or the interpreter where the package is installed:

```sh
9lives --version
9lives mcp
/path/to/python -m ninelives.cli heal tests/login.spec.ts
```

The Python package continues to provide its existing `9l` and `9lives` entry points. Install it explicitly with `pip install 9lives` or `uv tool install 9lives` when a workflow still needs it. Select the intended executable in each script rather than relying on PATH order.

## Migrate Playwright execution first

Go uses your existing Playwright configuration, including global setup and teardown. Install project dependencies and the browsers your suite uses before running; Go never downloads tooling during execution. Preserve existing assertions. The optional `@9l/playwright` SDK is not required for ordinary specs.

These examples assume `9l --version` identifies the Go runner:

```sh
# Inspect discovery before executing any tests.
9l plan tests/ --format json
9l run tests/ --workers 2 --timeout 5m --deadline 20m \
  --pass-env BASE_URL,TEST_USER --format json
# Use the run ID printed when the run starts.
9l status <run-id>
9l result <run-id> --format json
9l cancel <run-id>
```

Do not treat Go as a drop-in replacement in existing scripts:

| Python behavior | Go migration |
| --- | --- |
| `9lives run --run-timeout 900 <spec>` | `9l run <spec> --timeout 15m`; native healing uses its own `--run-timeout` option |
| Application environment inherited by tests | Name required keys with `--pass-env`; values are not persisted in receipts |
| `--framework auto/cypress/selenium/playwright` | Go execution currently supports Playwright; retain Python for other adapters |
| Bare spec scaffolds a temporary Playwright project | Set up a real project and install local tooling, or retain Python scaffolding |
| Python `.9lives-report.md`, history, and artifacts | Go terminal receipts live in `.9lives/receipts/`; migrate consumers explicitly |
| Python command output and exit codes | Use the pinned Go release's JSON and exit behavior; update and test consumers |

Start with a representative subset. Compare test discovery, passing and failing outcomes, skips, interruption, environment settings, and artifact consumers against the existing workflow. Go `--attempts` does not replace Playwright's configured retries; review both budgets before migrating. A passing receipt means execution and evidence validation succeeded, not that assertions fully cover requirements. See the [CLI reference](https://github.com/Quality-Max/9lives-runner/blob/main/docs/cli.md).

## Healing and workflows that still use Python

| Workflow | Transition status |
| --- | --- |
| Playwright execution | Prefer Go after validating the project workflow |
| `9lives heal` | Supported Python path. Go v0.1.5 and earlier: `9l heal` delegates to Python. From the release after v0.1.5, Go `9l heal` is native (see below) |
| Native selector repair | Go `tier1` produces offline, unverified proposals; `heal-native` (and, after v0.1.5, `9l heal`) verifies supported selector-only changes in isolation |
| MCP `heal_test` / `run_test` | Python's `9lives mcp` remains available. From the release after v0.1.5, Go `9l mcp` is a native server with `run_test`, `heal_test` and `assess_test`; v0.1.5 and earlier have no `mcp` command |
| Watch, brittle-selector history/report, doctor | Retain Python until replacements or discontinuation decisions are documented |
| Cypress/Selenium execution | Retain Python; Go adapters are deferred |
| Standalone-spec scaffolding | Retain Python or set up a Playwright project explicitly |
| GitHub Action and pre-commit hooks | Existing integrations remain Python; migrate each explicitly |

Native healing is deliberately narrower than historical Python repair behavior. It refuses assertion edits and unrelated source changes. Review the [Tier 1](https://github.com/Quality-Max/9lives-runner/blob/main/docs/native-tier1.md) and [native healing](https://github.com/Quality-Max/9lives-runner/blob/main/docs/native-tier2.md) contracts before adopting it. Do not equate an offline proposal with a verified repair.

Go v0.1.5 and earlier run `9l heal` through the separately installed Python package (`python3 -m ninelives.cli heal`, or the interpreter in `NINELIVES_PYTHON`) and have no `9l mcp`. From the release after v0.1.5, neither needs Python:

- `9l heal <spec>` runs Go's verified selector healing: one offline Tier 1 attempt, then the provider named with `--provider` or `NINELIVES_PROVIDER`, an installed `claude`/`codex`/`opencode` CLI, or a configured API key. With no provider it is offline Tier 1 only. Each candidate is verified in an isolated copy before it is saved as `<spec>.healed` or, with approval or `--yes`, applied. Output is a JSON session result, not Python's report. `--run-timeout` accepts whole seconds as before. Python-only options such as `--framework` exit 2; use `9lives heal` for them and for Cypress or Selenium specs.
- `9l mcp` is a native MCP stdio server with `run_test`, `heal_test` and `assess_test`. Start it in the project root and name the environment variables tests need: `claude mcp add 9lives -- 9l mcp --pass-env BASE_URL`. Paths outside the working directory are refused unless `NINELIVES_MCP_UNRESTRICTED=1`, as in Python. `heal_test` writes in place only with `apply: true`. See the [MCP server guide](https://github.com/Quality-Max/9lives-runner/blob/main/docs/mcp.md).

To keep Python's MCP server, configure hosts with `9lives mcp`, or an absolute Python interpreter and `-m ninelives.cli mcp`, so a Go installation does not change the server selected by PATH. A host configured with `9l mcp` stops connecting when Go v0.1.5 or earlier is first on PATH. Keep stdout reserved for MCP protocol messages.

The Action and hooks in this repository select `ninelives.cli` through their Python interpreter. Existing published tags stay on their current implementation; these changes take effect only when users select a release containing them. New Go CI integrations must explicitly pin the runner release, preserve application setup, map receipts and exit codes, and verify both a passing test and a known failure. Do not retarget the `v1` Action tag to Go.

## Retirement gates

This documentation starts the transition; it does not remove any Python command or establish an end-of-support deadline. Before retiring a workflow:

1. Publish its replacement or an explicit discontinuation decision, including migration and rollback instructions.
2. Qualify it on representative user projects: discovery, known failures, skips, cancellation/timeouts, repair approval and assertion preservation, plus any integration contracts it owns.
3. Show successful migration across at least two stable Go releases. Release count alone is not evidence of compatibility.
4. Announce a dated support window and any breaking entry-point or distribution changes before removal.

Keep the last supported Python release available and preserve pinned source revisions used as differential compatibility oracles. Those test fixtures can outlive Python's runtime distribution. Security and correctness fixes remain in scope throughout the announced maintenance period.
