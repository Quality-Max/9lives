"""Framework adapters — make the heal verb framework-agnostic.

`9l heal` speaks Playwright natively; these adapters extend the same
run → classify → heal loop to Cypress and Selenium (pytest) specs. Each
adapter knows how to run one spec and return a `RunResult`; everything
downstream (classification, Tier 1 anchors, Tier 2 prompts, diffs,
reports, history) is shared.
"""

import json
import re
from pathlib import Path

from ..runner.project import find_enclosing_package_json
from .cypress import CypressAdapter
from .playwright import PlaywrightAdapter
from .selenium import SeleniumAdapter

FRAMEWORKS = ("playwright", "cypress", "selenium")

_ADAPTERS = {
    "playwright": PlaywrightAdapter(),
    "cypress": CypressAdapter(),
    "selenium": SeleniumAdapter(),
}

_CYPRESS_SUFFIX = re.compile(r"\.cy\.[cm]?[jt]sx?$", re.IGNORECASE)


def detect_framework(spec: Path) -> str:
    """Infer the test framework for a spec file.

    Order: the `.cy.*` naming convention, then Python (Selenium runs via
    pytest), then the enclosing package.json's dependencies — a project
    that depends on cypress but not @playwright/test is a Cypress project
    even for plain `.spec.js` names. Playwright is the default.
    """
    name = spec.name.lower()
    if _CYPRESS_SUFFIX.search(name):
        return "cypress"
    if name.endswith(".py"):
        return "selenium"

    pkg_dir = find_enclosing_package_json(spec.resolve().parent)
    if pkg_dir:
        try:
            data = json.loads((pkg_dir / "package.json").read_text())
        except (OSError, json.JSONDecodeError):
            return "playwright"
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "cypress" in deps and "@playwright/test" not in deps:
            return "cypress"
    return "playwright"


def get_adapter(spec: Path, framework: str = "auto"):
    """Resolve the adapter for a spec, honoring an explicit --framework."""
    name = framework if framework and framework != "auto" else detect_framework(spec)
    if name not in _ADAPTERS:
        raise ValueError(f"Unknown framework: {name} (expected one of {', '.join(FRAMEWORKS)})")
    return _ADAPTERS[name]
