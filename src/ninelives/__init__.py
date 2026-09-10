"""9lives — self-healing QA for the coding-agent era."""

# The only place the version lives. pyproject.toml declares `version` dynamic
# and hatch reads it from here, so `9l --version` and the published package can
# no longer disagree (0.1.1–0.1.3 shipped reporting 0.1.0).
__version__ = "0.2.1"
