#!/usr/bin/env python3
"""Fold a multi-file Harbor Chart page into one self-contained HTML document.

Author a document normally — `<link>` to `assets/tokens.css`, `<img>` the mark,
`<script src>` the behavior — then bundle it. Stylesheets and scripts become
inline blocks; fonts, images, and any other `url()` target become base64 data
URIs. The result opens correctly from a mail attachment, a USB stick, or
`file://` with no network and no sibling files.

Stdlib only, and deliberately offline: a remote `https://` reference is a
self-containment violation to report, never something to fetch.

    bundle_html.py SOURCE -o OUT.html          # bundle, then verify
    bundle_html.py --check OUT.html            # verify only
    bundle_html.py SOURCE -o OUT.html \
        --fonts overpass/400,overpass/700,overpass-mono/500

Exit codes: 0 clean, 1 violation or missing asset, 2 usage.
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

MIME_BY_SUFFIX = {
    ".avif": "image/avif",
    ".css": "text/css",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript",
    ".json": "application/json",
    ".otf": "font/otf",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

# Schemes and fragment-only targets that are already self-contained or are not
# ours to resolve.
EXTERNAL_SCHEME_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)
INLINE_SAFE_RE = re.compile(r"^(?:data:|#|$)")

LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>\s*</script\s*>", re.IGNORECASE)
SRC_TAG_RE = re.compile(r"<(img|source|iframe|video|audio|embed)\b[^>]*>", re.IGNORECASE)
ANCHOR_TAG_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]*\}", re.IGNORECASE)
IMPORT_RE = re.compile(
    r"""@import\s+(?:url\(\s*)?["']?([^"')\s]+)["']?\s*\)?\s*([^;]*);""",
    re.IGNORECASE,
)
CSS_URL_RE = re.compile(r"""url\(\s*(["']?)([^"')]+)\1\s*\)""", re.IGNORECASE)
MAX_IMPORT_DEPTH = 8

# Fonts alone can dominate a document; flag anything unusually heavy so the
# author can reach for a smaller derivative or a shorter font set.
DEFAULT_WARN_BYTES = 320 * 1024


class BundleError(Exception):
    """A referenced asset could not be resolved."""


@dataclass
class Record:
    kind: str
    ref: str
    bytes_in: int


@dataclass
class Report:
    inlined: list[Record] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def attr(tag: str, name: str) -> str | None:
    match = re.search(
        rf"""\b{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""",
        tag,
        re.IGNORECASE,
    )
    if not match:
        return None
    return next(group for group in match.groups() if group is not None)


def is_local_ref(ref: str | None) -> bool:
    """True when the reference points at a file we are expected to inline."""
    if ref is None:
        return False
    ref = ref.strip()
    if not ref or INLINE_SAFE_RE.match(ref):
        return False
    return not EXTERNAL_SCHEME_RE.match(ref)


def rel_tokens(tag: str) -> set[str]:
    return {token.lower() for token in (attr(tag, "rel") or "").split()}


def mime_for(path: Path) -> str:
    return MIME_BY_SUFFIX.get(path.suffix.lower(), "application/octet-stream")


def parse_font_selectors(spec: str) -> set[str] | None:
    """`overpass/400,overpass-mono/500` -> {'overpass/400', 'overpass-mono/500'}.

    `all` keeps every face; `none` drops them all.
    """
    spec = spec.strip().lower()
    if spec == "all":
        return None
    if spec == "none":
        return set()
    selectors = {token.strip() for token in spec.split(",") if token.strip()}
    for selector in selectors:
        if "/" not in selector:
            raise SystemExit(
                f"bundle: --fonts expects family/weight pairs; got '{selector}'"
            )
    return selectors


def font_face_selector(block: str) -> str | None:
    family = re.search(
        r"""font-family\s*:\s*["']?([^;"']+)["']?\s*;""", block, re.IGNORECASE
    )
    if not family:
        return None
    weight = re.search(r"font-weight\s*:\s*(\d+)", block, re.IGNORECASE)
    normalized = re.sub(r"\s+", "-", family.group(1).strip().lower())
    return f"{normalized}/{weight.group(1) if weight else '400'}"


class Bundler:
    def __init__(self, fonts: set[str] | None, warn_bytes: int) -> None:
        self.fonts = fonts
        self.warn_bytes = warn_bytes
        self.report = Report()

    def read(self, base_dir: Path, ref: str) -> tuple[Path, bytes]:
        path = (base_dir / ref.split("?", 1)[0].split("#", 1)[0]).resolve()
        try:
            return path, path.read_bytes()
        except OSError as error:
            raise BundleError(f"cannot read '{ref}' (resolved to {path}): {error}")

    def data_uri(self, kind: str, base_dir: Path, ref: str) -> str:
        path, raw = self.read(base_dir, ref)
        self.note(kind, ref, len(raw))
        encoded = base64.b64encode(raw).decode("ascii")
        return f"data:{mime_for(path)};base64,{encoded}"

    def note(self, kind: str, ref: str, size: int) -> None:
        # Every occurrence costs its own copy of the bytes, so a repeat is worth
        # surfacing: the fix is usually one reference plus a runtime assignment.
        if any(record.ref == ref for record in self.report.inlined):
            self.report.warnings.append(
                f"{ref} inlined more than once (+{size * 4 // 3 // 1024} KB each time)"
            )
        self.report.inlined.append(Record(kind, ref, size))
        if size > self.warn_bytes:
            self.report.warnings.append(
                f"{ref} is {size // 1024} KB before base64 (~{size * 4 // 3 // 1024} KB "
                f"inlined); consider a smaller derivative"
            )

    def keep_font_face(self, block: str) -> bool:
        if self.fonts is None:
            return True
        selector = font_face_selector(block)
        return selector in self.fonts if selector else True

    def filter_font_faces(self, css: str) -> str:
        if self.fonts is None:
            return css

        def replace(match: re.Match[str]) -> str:
            block = match.group(0)
            if self.keep_font_face(block):
                return block
            self.report.dropped.append(
                f"@font-face {font_face_selector(block) or '?'} (not in --fonts)"
            )
            return ""

        return FONT_FACE_RE.sub(replace, css)

    def inline_css(self, css: str, base_dir: Path, depth: int = 0) -> str:
        if depth > MAX_IMPORT_DEPTH:
            raise BundleError(f"@import nested deeper than {MAX_IMPORT_DEPTH} levels")

        def expand_import(match: re.Match[str]) -> str:
            ref, media = match.group(1), match.group(2).strip()
            if not is_local_ref(ref):
                return match.group(0)
            path, raw = self.read(base_dir, ref)
            self.note("@import", ref, len(raw))
            nested = self.inline_css(raw.decode("utf-8"), path.parent, depth + 1)
            nested = self.filter_font_faces(nested)
            return f"@media {media} {{\n{nested}\n}}" if media else nested

        css = IMPORT_RE.sub(expand_import, css)
        css = self.filter_font_faces(css)

        def expand_url(match: re.Match[str]) -> str:
            ref = match.group(2)
            if not is_local_ref(ref):
                return match.group(0)
            return f'url("{self.data_uri("url()", base_dir, ref)}")'

        return CSS_URL_RE.sub(expand_url, css)

    def inline_html(self, html: str, base_dir: Path) -> str:
        html = LINK_TAG_RE.sub(lambda m: self.replace_link(m.group(0), base_dir), html)
        html = SCRIPT_TAG_RE.sub(
            lambda m: self.replace_script(m.group(0), base_dir), html
        )
        return SRC_TAG_RE.sub(lambda m: self.replace_src(m.group(0), base_dir), html)

    def replace_link(self, tag: str, base_dir: Path) -> str:
        rels = rel_tokens(tag)
        href = attr(tag, "href")
        if not is_local_ref(href):
            return tag
        assert href is not None
        if {"preload", "modulepreload", "prefetch"} & rels:
            # Inlined bytes need no preload hint, and keeping one would ship the
            # payload twice.
            self.report.dropped.append(f"<link rel={'/'.join(sorted(rels))}> {href}")
            return ""
        if "stylesheet" in rels:
            path, raw = self.read(base_dir, href)
            self.note("stylesheet", href, len(raw))
            css = self.inline_css(raw.decode("utf-8"), path.parent)
            media = attr(tag, "media")
            media_attr = f' media="{media}"' if media else ""
            return f"<style{media_attr}>\n{css.strip()}\n</style>"
        return re.sub(
            r"""href\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+)""",
            lambda _: f'href="{self.data_uri("link", base_dir, href)}"',
            tag,
            count=1,
        )

    def replace_script(self, tag: str, base_dir: Path) -> str:
        src = attr(tag, "src")
        if not is_local_ref(src):
            return tag
        assert src is not None
        path, raw = self.read(base_dir, src)
        self.note("script", src, len(raw))
        body = raw.decode("utf-8")
        if path.suffix.lower() == ".js":
            # A literal </script> inside the source would close the block early.
            body = re.sub(r"</\s*script", r"<\\/script", body, flags=re.IGNORECASE)
        type_attr = ' type="module"' if attr(tag, "type") == "module" else ""
        return f"<script{type_attr}>\n{body.strip()}\n</script>"

    def replace_src(self, tag: str, base_dir: Path) -> str:
        if is_local_ref(attr(tag, "srcset")):
            self.report.warnings.append(
                "srcset is not inlined; give the element a single src instead"
            )
        src = attr(tag, "src")
        if not is_local_ref(src):
            return tag
        assert src is not None
        return re.sub(
            r"""src\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+)""",
            lambda _: f'src="{self.data_uri("src", base_dir, src)}"',
            tag,
            count=1,
        )


def find_violations(html: str) -> tuple[list[str], list[str]]:
    """Return (fatal, advisory) leftover references in a supposedly bundled doc."""
    fatal: list[str] = []
    advisory: list[str] = []

    for tag in LINK_TAG_RE.findall(html):
        href = attr(tag, "href")
        if href and not INLINE_SAFE_RE.match(href.strip()):
            rels = "/".join(sorted(rel_tokens(tag))) or "link"
            fatal.append(f"<link rel={rels}> href={href}")
    for tag in re.findall(r"<script\b[^>]*>", html, re.IGNORECASE):
        src = attr(tag, "src")
        if src and not INLINE_SAFE_RE.match(src.strip()):
            fatal.append(f"<script src={src}>")
    for match in SRC_TAG_RE.finditer(html):
        tag = match.group(0)
        for name in ("src", "srcset", "poster"):
            value = attr(tag, name)
            if value and not INLINE_SAFE_RE.match(value.strip()):
                fatal.append(f"<{match.group(1).lower()} {name}={value}>")
    for match in CSS_URL_RE.finditer(html):
        ref = match.group(2).strip()
        if not INLINE_SAFE_RE.match(ref):
            fatal.append(f"url({ref})")
    for tag in ANCHOR_TAG_RE.findall(html):
        href = attr(tag, "href")
        if href and is_local_ref(href):
            advisory.append(f"<a href={href}> (dead link outside its folder)")
    return fatal, advisory


def emit_report(report: Report, out_label: str, out_bytes: int, quiet: bool) -> None:
    if quiet:
        return
    for record in report.inlined:
        print(
            f"  inlined  {record.kind:<11} {record.ref}  "
            f"({record.bytes_in // 1024 or 1} KB)",
            file=sys.stderr,
        )
    for item in report.dropped:
        print(f"  dropped  {item}", file=sys.stderr)
    for warning in report.warnings:
        print(f"  warning  {warning}", file=sys.stderr)
    print(
        f"bundle: {out_label} — {len(report.inlined)} asset(s), "
        f"{out_bytes // 1024} KB self-contained",
        file=sys.stderr,
    )


def check(path: Path, strict: bool, quiet: bool) -> int:
    fatal, advisory = find_violations(path.read_text(encoding="utf-8"))
    for item in fatal:
        print(f"  external {item}", file=sys.stderr)
    for item in advisory:
        print(f"  warning  {item}", file=sys.stderr)
    if fatal or (strict and advisory):
        print(f"check: {path} is NOT self-contained", file=sys.stderr)
        return 1
    if not quiet:
        print(f"check: {path} is self-contained", file=sys.stderr)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bundle_html.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", help="HTML to bundle, or to verify with --check")
    parser.add_argument("-o", "--out", help="output path; '-' for stdout")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify SOURCE is already self-contained; write nothing",
    )
    parser.add_argument(
        "--fonts",
        default="all",
        help="font faces to keep: 'all', 'none', or family/weight pairs "
        "(e.g. overpass/400,overpass/700,overpass-mono/500)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat advisory findings (sibling-file links) as failures",
    )
    parser.add_argument(
        "--warn-bytes",
        type=int,
        default=DEFAULT_WARN_BYTES,
        help=f"warn above this pre-base64 asset size (default {DEFAULT_WARN_BYTES})",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="errors only")
    args = parser.parse_args(argv)
    if not args.check and not args.out:
        parser.error("-o/--out is required unless --check is given")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = Path(args.source)
    if not source.is_file():
        print(f"bundle: no such file: {source}", file=sys.stderr)
        return 1
    if args.check:
        return check(source, args.strict, args.quiet)

    bundler = Bundler(parse_font_selectors(args.fonts), args.warn_bytes)
    try:
        bundled = bundler.inline_html(
            source.read_text(encoding="utf-8"), source.resolve().parent
        )
    except BundleError as error:
        print(f"bundle: {error}", file=sys.stderr)
        return 1

    fatal, advisory = find_violations(bundled)
    bundler.report.warnings.extend(
        f"{item} — use an in-document #anchor instead" for item in advisory
    )
    if args.out == "-":
        sys.stdout.write(bundled)
        out_label = "<stdout>"
    else:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(bundled, encoding="utf-8")
        out_label = str(out_path)
    emit_report(
        bundler.report, out_label, len(bundled.encode("utf-8")), args.quiet
    )

    if fatal:
        for item in fatal:
            print(f"  external {item}", file=sys.stderr)
        print("bundle: output still references external files", file=sys.stderr)
        return 1
    if args.strict and advisory:
        print("bundle: advisory findings with --strict", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
