#!/usr/bin/env bash
# Regenerate heal.gif from the demo using asciinema + agg.
#   deps: asciinema, agg, 9l (or NINE="python3 -m ninelives.cli"), node
set -euo pipefail
cd "$(dirname "$0")"
NINE="${NINE:-9l}"
git checkout -- login.spec.js 2>/dev/null || true
python3 -m http.server 8137 --directory site >/dev/null 2>&1 & SRV=$!
trap 'kill "$SRV" 2>/dev/null || true' EXIT
sleep 1
runner="$(mktemp)"
cat > "$runner" <<INNER
printf '\033[38;5;213m\$ \033[1;38;5;51m9l heal login.spec.js\033[0m\n\n'
sleep 0.8
DEMO_URL=http://localhost:8137 $NINE heal --yes login.spec.js
sleep 1.2
INNER
asciinema record -c "bash $runner" --overwrite --idle-time-limit 1.2 heal.cast
agg --font-size 22 --theme asciinema heal.cast heal.gif
rm -f "$runner"
echo "wrote heal.gif"
