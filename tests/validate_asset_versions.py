#!/usr/bin/env python3
"""Fail if any local ?v= in public/*.html does not match the file's SHA-256."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

ASSET_RE = re.compile(
    r"""(?:href|src)=["'](/(?:css|js)/[^"'?#]+)\?v=([^"'#]*)["']""",
    re.I,
)

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def file_version(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:10]


def main() -> int:
    pages = sorted(p for p in PUBLIC.glob("*.html") if p.is_file())
    if not pages:
        fail("no public/*.html pages found")
        print("FAIL")
        for err in errors:
            print(" -", err)
        return 1

    seen = 0
    for page in pages:
        rel = page.relative_to(ROOT)
        html = page.read_text(encoding="utf-8")
        matches = list(ASSET_RE.finditer(html))
        if not matches:
            # 404.html and others still load /css/styles.css; require a version.
            if re.search(r"""(?:href|src)=["']/(?:css|js)/""", html, re.I):
                fail(f"{rel}: local /js/ or /css/ reference has no ?v=")
            continue
        for match in matches:
            url_path, version = match.group(1), match.group(2)
            asset = PUBLIC / url_path.lstrip("/")
            if not asset.is_file():
                fail(f"{rel}: {url_path} does not exist")
                continue
            expected = file_version(asset)
            seen += 1
            if version != expected:
                fail(
                    f"{rel}: {url_path}?v={version} != sha256[:10] {expected}"
                )

    if not seen:
        fail("no versioned local /js/ or /css/ references found in public/*.html")

    if errors:
        print("FAIL")
        for err in errors:
            print(" -", err)
        return 1
    print("PASS")
    print(f" pages={len(pages)} versioned_refs={seen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
