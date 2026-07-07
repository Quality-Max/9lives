#!/bin/sh
# 9lives installer — served at https://9l.run (and https://9lives.run/i)
#   curl -sL 9l.run | sh
#
# Installs the 9lives CLI (`9l`) into an isolated environment via uv.
# No account, no telemetry. MIT. https://github.com/Quality-Max/9lives
set -e

PAW="🐾"

say() { printf '%s %s\n' "$PAW" "$1"; }

# 1. Ensure uv (installs Python itself if needed, keeps 9lives isolated)
if ! command -v uv >/dev/null 2>&1; then
  say "installing uv (isolated Python package manager) …"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Pick up the fresh install for this shell
  export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Install/upgrade 9lives with both LLM extras (subscription mode needs neither)
say "installing 9lives …"
uv tool install --upgrade '9lives[all]' >/dev/null

# 3. Sanity check
if command -v 9l >/dev/null 2>&1; then
  say "installed: $(9l --version)"
else
  say "installed — open a new shell (or add ~/.local/bin to PATH), then run: 9l doctor"
  exit 0
fi

say "next steps:"
printf '   9l doctor            # check node/playwright/agent CLIs\n'
printf '   9l heal your.spec.ts # resurrect a failing test\n'
say "your tests have nine lives."
