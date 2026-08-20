"""Offline tests for sykesdev-design-system bundle_html.py.

Exercised through the CLI: HTML and assets in, one self-contained file out.
No browser and no network, so these run anywhere CI does.
"""

from __future__ import annotations

import base64
from pathlib import Path

from conftest import SKILLS_DIR, run_script

SKILL = "sykesdev-design-system"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8AAAAMBAQA"
    "OQZ8AAAAASUVORK5CYII="
)


def _run(*args: str, cwd: Path | None = None):
    return run_script(SKILL, "bundle_html.py", *args, cwd=cwd)


def _site(tmp_path: Path) -> Path:
    """A miniature multi-file page: stylesheet, font, image, script, import."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "mark.png").write_bytes(PNG)
    (assets / "face.woff2").write_bytes(b"woff2-bytes")
    (assets / "base.css").write_text(":root { --ink: #0b1018; }\n", encoding="utf-8")
    (assets / "site.css").write_text(
        '@import "base.css";\n'
        "@font-face { font-family: Overpass; font-weight: 400;"
        ' src: url("face.woff2") format("woff2"); }\n'
        "@font-face { font-family: 'Overpass Mono'; font-weight: 700;"
        ' src: url("face.woff2") format("woff2"); }\n'
        "body { background: var(--ink) url(mark.png); }\n",
        encoding="utf-8",
    )
    (assets / "app.js").write_text(
        'document.title = "bundled";\n', encoding="utf-8"
    )
    page = tmp_path / "page.html"
    page.write_text(
        "<!doctype html><html><head>"
        '<link rel="preload" as="font" href="assets/face.woff2">'
        '<link rel="stylesheet" href="assets/site.css">'
        "</head><body>"
        '<img src="assets/mark.png" alt="mark">'
        '<script src="assets/app.js"></script>'
        "</body></html>\n",
        encoding="utf-8",
    )
    return page


def test_bundle_inlines_every_local_asset(tmp_path: Path) -> None:
    page = _site(tmp_path)
    out = tmp_path / "out" / "bundled.html"

    proc = _run(str(page), "-o", str(out))

    assert proc.returncode == 0, proc.stderr
    text = out.read_text(encoding="utf-8")
    assert "<style>" in text
    assert 'document.title = "bundled"' in text
    assert "--ink: #0b1018" in text, "@import was not resolved"
    assert text.count("data:font/woff2;base64,") == 2
    assert "data:image/png;base64," in text
    for external in ("assets/site.css", "assets/app.js", "assets/mark.png"):
        assert external not in text


def test_bundle_drops_preload_hints(tmp_path: Path) -> None:
    """Preloading bytes that are already inline would ship them twice."""
    page = _site(tmp_path)
    out = tmp_path / "bundled.html"

    proc = _run(str(page), "-o", str(out))

    assert proc.returncode == 0, proc.stderr
    assert 'rel="preload"' not in out.read_text(encoding="utf-8")
    assert "dropped" in proc.stderr


def test_bundle_output_passes_its_own_check(tmp_path: Path) -> None:
    page = _site(tmp_path)
    out = tmp_path / "bundled.html"
    assert _run(str(page), "-o", str(out)).returncode == 0

    proc = _run("--check", str(out))

    assert proc.returncode == 0, proc.stderr
    assert "is self-contained" in proc.stderr


def test_check_rejects_a_page_with_external_references(tmp_path: Path) -> None:
    page = _site(tmp_path)

    proc = _run("--check", str(page))

    assert proc.returncode == 1
    assert "NOT self-contained" in proc.stderr


def test_check_rejects_a_remote_stylesheet(tmp_path: Path) -> None:
    """Remote references are reported, never fetched: bundling stays offline."""
    page = tmp_path / "remote.html"
    page.write_text(
        '<link rel="stylesheet" href="https://fonts.example/x.css">',
        encoding="utf-8",
    )

    proc = _run("--check", str(page))

    assert proc.returncode == 1
    assert "fonts.example" in proc.stderr


def test_fonts_selector_keeps_only_named_faces(tmp_path: Path) -> None:
    page = _site(tmp_path)
    out = tmp_path / "lean.html"

    proc = _run(str(page), "-o", str(out), "--fonts", "overpass/400")

    assert proc.returncode == 0, proc.stderr
    text = out.read_text(encoding="utf-8")
    assert text.count("@font-face") == 1
    assert "Overpass Mono" not in text
    assert "overpass-mono/700" in proc.stderr


def test_fonts_none_drops_every_face(tmp_path: Path) -> None:
    page = _site(tmp_path)
    out = tmp_path / "systemfont.html"

    proc = _run(str(page), "-o", str(out), "--fonts", "none")

    assert proc.returncode == 0, proc.stderr
    text = out.read_text(encoding="utf-8")
    assert "@font-face" not in text
    assert "data:font/woff2" not in text
    # The background image still resolves; only the faces went away.
    assert "data:image/png;base64," in text


def test_malformed_font_selector_is_rejected(tmp_path: Path) -> None:
    page = _site(tmp_path)

    proc = _run(str(page), "-o", str(tmp_path / "x.html"), "--fonts", "overpass")

    assert proc.returncode != 0
    assert "family/weight" in proc.stderr


def test_missing_asset_fails_loudly(tmp_path: Path) -> None:
    page = tmp_path / "broken.html"
    page.write_text('<link rel="stylesheet" href="gone.css">', encoding="utf-8")

    proc = _run(str(page), "-o", str(tmp_path / "out.html"))

    assert proc.returncode == 1
    assert "gone.css" in proc.stderr


def test_sibling_links_warn_and_fail_only_under_strict(tmp_path: Path) -> None:
    page = tmp_path / "linked.html"
    page.write_text('<a href="other.html">next</a>', encoding="utf-8")

    lenient = _run(str(page), "-o", str(tmp_path / "a.html"))
    strict = _run(str(page), "-o", str(tmp_path / "b.html"), "--strict")

    assert lenient.returncode == 0, lenient.stderr
    assert "other.html" in lenient.stderr
    assert strict.returncode == 1


def test_duplicate_asset_is_reported(tmp_path: Path) -> None:
    page = tmp_path / "twice.html"
    (tmp_path / "mark.png").write_bytes(PNG)
    page.write_text(
        '<img src="mark.png" alt="a"><img src="mark.png" alt="b">', encoding="utf-8"
    )

    proc = _run(str(page), "-o", str(tmp_path / "out.html"))

    assert proc.returncode == 0, proc.stderr
    assert "more than once" in proc.stderr


def test_script_closing_tag_in_source_is_escaped(tmp_path: Path) -> None:
    """A literal </script> in the source would otherwise end the inline block."""
    page = tmp_path / "tricky.html"
    (tmp_path / "app.js").write_text(
        'const t = "</script>";\n', encoding="utf-8"
    )
    page.write_text('<script src="app.js"></script>', encoding="utf-8")
    out = tmp_path / "out.html"

    proc = _run(str(page), "-o", str(out))

    assert proc.returncode == 0, proc.stderr
    body = out.read_text(encoding="utf-8")
    assert "<\\/script>" in body
    assert body.count("</script>") == 1


def test_shipped_template_bundles_clean() -> None:
    """The starter must stay bundleable: it is the documented entry point."""
    template = SKILLS_DIR / SKILL / "templates" / "document.html"

    proc = _run("--check", str(template))

    # Authored multi-file on purpose, so it must fail the check before bundling.
    assert proc.returncode == 1
    assert "tokens.css" in proc.stderr


def test_shipped_template_bundles_into_one_file(tmp_path: Path) -> None:
    template = SKILLS_DIR / SKILL / "templates" / "document.html"
    out = tmp_path / "document.html"

    proc = _run(
        str(template),
        "-o",
        str(out),
        "--fonts",
        "overpass/400,overpass/600,overpass/700,overpass/800,overpass-mono/500",
        "--strict",
    )

    assert proc.returncode == 0, proc.stderr
    text = out.read_text(encoding="utf-8")
    assert text.count("@font-face") == 5
    assert "../assets/" not in text, "a local reference survived bundling"
    assert "data:image/png;base64," in text
    assert _run("--check", str(out), "--strict").returncode == 0
