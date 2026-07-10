"""Heal history — the data only 9lives has.

Every heal attempt appends one JSON line to `.9lives/history.jsonl` next to
the spec. `9l report` aggregates those lines into a brittle-selector report:
which selectors keep rotting, which anchor keeps re-finding them, and what
to pin instead. Local files only — nothing is uploaded anywhere.
"""

import json
import logging
import time
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_FILENAME = "history.jsonl"


def history_path(spec: Path) -> Path:
    return spec.resolve().parent / ".9lives" / HISTORY_FILENAME


def record_heal(spec: Path, **fields) -> Path:
    """Append one heal-attempt record for a spec. Never raises into the heal loop."""
    path = history_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "spec": spec.name,
        "spec_path": str(spec.resolve()),
        **fields,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def load_history(root: Path) -> list[dict]:
    """Read every history file under `root` (skipping unparseable lines)."""
    records: list[dict] = []
    for path in sorted(root.resolve().rglob(f".9lives/{HISTORY_FILENAME}")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def selector_report(records: list[dict]) -> list[dict]:
    """Aggregate heal records into per-(spec, selector) rows, worst first."""
    groups: dict[tuple[str, str], dict] = {}
    for r in records:
        if r.get("status") == "passed":
            continue
        key = (r.get("spec") or "?", r.get("failed_selector") or "(unknown)")
        g = groups.setdefault(
            key,
            {
                "spec": key[0],
                "selector": key[1],
                "heals": 0,
                "unhealed": 0,
                "needs_human": 0,
                "anchors": Counter(),
                "last_new_selector": "",
                "first_ts": r.get("ts", ""),
                "last_ts": r.get("ts", ""),
            },
        )
        status = r.get("status")
        if status == "healed":
            g["heals"] += 1
            if r.get("healed_selector"):
                g["last_new_selector"] = r["healed_selector"]
        elif status == "needs-human":
            g["needs_human"] += 1
        else:
            g["unhealed"] += 1
        if r.get("anchor"):
            g["anchors"][r["anchor"]] += 1
        g["last_ts"] = max(g["last_ts"], r.get("ts", ""))
        g["first_ts"] = min(g["first_ts"], r.get("ts", "")) if r.get("ts") else g["first_ts"]

    rows = []
    for g in groups.values():
        g["top_anchor"] = g["anchors"].most_common(1)[0][0] if g["anchors"] else ""
        g["events"] = g["heals"] + g["unhealed"] + g["needs_human"]
        g["recommendation"] = _recommend(g)
        rows.append(g)
    rows.sort(key=lambda g: (g["events"], g["heals"]), reverse=True)
    return rows


def _recommend(g: dict) -> str:
    if g["needs_human"] and not g["heals"]:
        return "failures look behavioral — review the app/test, not the selector"
    if g["heals"] >= 2:
        return f"rotting — healed {g['heals']}×; pin a data-testid"
    if g["top_anchor"] == "text":
        return "text-anchored — copy changes break it; add a data-testid"
    if g["top_anchor"] == "class":
        return "class-anchored — styling churn breaks it; add a data-testid or id"
    if g["unhealed"] and not g["heals"]:
        return "never auto-healed — likely needs a rewrite"
    return "watch — one heal so far"


def render_report(rows: list[dict], markdown: bool = False) -> str:
    """Render the brittle-selector report for the terminal or as markdown."""
    total_heals = sum(r["heals"] for r in rows)
    title = f"🐾 brittle-selector report — {total_heals} heal(s) across {len(rows)} selector(s)"

    if not rows:
        return f"{title}\n\nno heal history yet — every `9l heal` run adds to .9lives/history.jsonl"

    if markdown:
        lines = [f"## {title}", "", "| selector | spec | heals | anchor | recommendation |", "|---|---|---|---|---|"]
        for r in rows:
            sel = r["selector"].replace("|", "\\|")
            lines.append(f"| `{sel}` | `{r['spec']}` | {r['heals']} | {r['top_anchor'] or '—'} | {r['recommendation']} |")
        lines.extend(["", "_generated locally by [9lives](https://9lives.run) `9l report` — data never leaves your machine_"])
        return "\n".join(lines)

    width = min(max((len(r["selector"]) for r in rows), default=8) + 2, 42)
    lines = [title, ""]
    lines.append(f"  {'selector':<{width}} {'spec':<24} {'heals':>5}  {'anchor':<10} recommendation")
    for r in rows:
        sel = r["selector"][: width - 1]
        lines.append(
            f"  {sel:<{width}} {r['spec'][:23]:<24} {r['heals']:>5}  {r['top_anchor'] or '—':<10} {r['recommendation']}"
        )
    return "\n".join(lines)
