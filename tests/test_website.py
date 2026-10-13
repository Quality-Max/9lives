from pathlib import Path

ROOT = Path(__file__).parents[1]
WEBSITE = ROOT / "website"


def test_public_installer_matches_canonical_script():
    assert (WEBSITE / "public" / "install.sh").read_bytes() == (ROOT / "install" / "9l.run.sh").read_bytes()


def test_landing_page_keeps_install_and_ecosystem_links():
    page = (WEBSITE / "app" / "page.tsx").read_text()

    assert "curl -fsSL https://9lives.run/install.sh | sh" in page
    assert "https://quality-max.github.io/9lives-runner/" in page
    assert "https://github.com/Quality-Max/9lives-runner" in page
    assert page.count('href="https://qualitymax.io"') == 2
    for destination in (
        "https://aiinqa.com/ai-in-qa-issue-18/",
        "https://github.com/Quality-Max/qmax-code",
        "https://github.com/Quality-Max/qualitymax-grader",
        "https://github.com/Quality-Max/free-qa-skills",
    ):
        assert destination in page


def test_landing_page_presents_the_page_checks_built_into_the_runner():
    page = (WEBSITE / "app" / "page.tsx").read_text()

    assert "https://qmax.run" not in page
    assert "9l scan https://your-app.dev --format markdown" in page
    assert "claude mcp add 9lives -- 9l mcp" in page
    for tool in ("scan_url", "inspect_page", "generate_playwright_repro", "confirm_finding"):
        assert tool in page


def test_installer_defaults_to_the_release_with_page_checks():
    installer = (ROOT / "install" / "9l.run.sh").read_text()

    assert 'VERSION="${NINELIVES_VERSION:-v0.4.0}"' in installer
    assert "9l scan" in installer


def test_site_uses_the_original_qualitymax_favicon():
    layout = (WEBSITE / "app" / "layout.tsx").read_text()

    assert "https://qualitymax.io/static/img/favicon-color-round.png" in layout


def test_root_uses_accept_header_for_installer_content_negotiation():
    proxy = (WEBSITE / "proxy.ts").read_text()

    assert "text/html" in proxy
    assert "'/install.sh'" in proxy
    assert "NextResponse.redirect" in proxy
    assert "matcher: ['/']" in proxy
