#!/usr/bin/env python3
"""Screenshot an HTML document headlessly so a chart can be judged, not assumed.

An audit that never looks at the artifact is a guess. This drives a locally
installed Chromium-family browser over `file://` — no server, no network, no
Node — and writes one PNG per viewport width under a temp directory by default.

The PNGs are for the agent (or author) to look at. They are not part of the
document. Do not write them next to the bundled HTML.

    render_check.py doc.html --widths 1440,760

Headless Chrome frequently writes its screenshot and then declines to exit, so
each run is given a deadline and killed once the file lands.

Exit codes: 0 all shots written, 1 no browser or a shot failed, 2 usage.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "brave-browser",
    "microsoft-edge",
)


def find_browser(override: str | None) -> str | None:
    for candidate in ([override] if override else []) + list(CANDIDATES):
        if not candidate:
            continue
        if Path(candidate).is_file():
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def shoot(browser: str, url: str, out: Path, width: int, height: int, wait_ms: int,
          profile: Path) -> bool:
    out.unlink(missing_ok=True)
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profile}",
        f"--window-size={width},{height}",
        f"--virtual-time-budget={wait_ms}",
        f"--screenshot={out}",
        url,
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        process.wait(timeout=(wait_ms / 1000) + 20)
    except subprocess.TimeoutExpired:
        # The PNG is written before shutdown; the hang is in teardown.
        process.kill()
        process.wait(timeout=10)
    return out.is_file() and out.stat().st_size > 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="render_check.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("document", help="HTML file to render")
    parser.add_argument(
        "-o",
        "--out-dir",
        default=None,
        help="directory for PNGs (default: a temp dir; these are for judging, not shipping)",
    )
    parser.add_argument("--widths", default="1440,760",
                        help="comma-separated viewport widths (default 1440,760)")
    parser.add_argument("--height", type=int, default=1000, help="viewport height")
    parser.add_argument("--wait-ms", type=int, default=2500,
                        help="virtual time budget before the shot")
    parser.add_argument("--browser", help="explicit browser binary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    document = Path(args.document)
    if not document.is_file():
        print(f"render: no such file: {document}", file=sys.stderr)
        return 1

    browser = find_browser(args.browser)
    if not browser:
        print(
            "render: no Chromium-family browser found; pass --browser PATH",
            file=sys.stderr,
        )
        return 1

    if args.out_dir is None:
        out_dir = Path(tempfile.mkdtemp(prefix="harbor-shots-"))
    else:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    profile = out_dir / ".render-profile"
    url = document.resolve().as_uri()

    failed = False
    for token in args.widths.split(","):
        width = int(token.strip())
        out = out_dir / f"{document.stem}-{width}.png"
        if shoot(browser, url, out, width, args.height, args.wait_ms, profile):
            print(f"render: {out} ({out.stat().st_size // 1024} KB, {width}px)")
        else:
            print(f"render: FAILED at {width}px", file=sys.stderr)
            failed = True

    shutil.rmtree(profile, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
