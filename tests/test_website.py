from pathlib import Path

ROOT = Path(__file__).parents[1]
WEBSITE = ROOT / "website"


def test_public_installer_matches_canonical_script():
    assert (WEBSITE / "public" / "install.sh").read_bytes() == (ROOT / "install" / "9l.run.sh").read_bytes()


def test_landing_page_keeps_install_and_ecosystem_links():
    page = (WEBSITE / "app" / "page.tsx").read_text()

    assert "curl -sL 9lives.run | sh" in page
    assert page.count('href="https://qualitymax.io"') == 2
    for destination in (
        "https://qmax.run",
        "https://github.com/Quality-Max/qmax-code",
        "https://github.com/Quality-Max/qualitymax-grader",
        "https://github.com/Quality-Max/free-qa-skills",
    ):
        assert destination in page


def test_site_uses_the_original_qualitymax_favicon():
    layout = (WEBSITE / "app" / "layout.tsx").read_text()

    assert "https://qualitymax.io/static/img/favicon-color-round.png" in layout


def test_root_uses_accept_header_for_installer_content_negotiation():
    proxy = (WEBSITE / "proxy.ts").read_text()

    assert "text/html" in proxy
    assert "'/install.sh'" in proxy
    assert "NextResponse.redirect" in proxy
    assert "matcher: ['/']" in proxy
