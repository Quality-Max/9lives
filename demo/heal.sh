#!/usr/bin/env bash
# 🐾 9lives demo — break a selector, watch it heal itself. No API key needed
# (Tier 1 is fully offline). Requires: Python 9lives on PATH + Node.js.
set -euo pipefail
cd "$(dirname "$0")"
git checkout -- login.spec.js 2>/dev/null || true   # reset to the "broken" state
python3 -m http.server 8137 --directory site >/dev/null 2>&1 & SRV=$!
trap 'kill "$SRV" 2>/dev/null || true' EXIT
sleep 1
DEMO_URL="http://localhost:8137" 9lives heal login.spec.js
