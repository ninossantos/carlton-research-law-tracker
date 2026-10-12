#!/usr/bin/env python3
"""Rewrite ?v= on local /js/ and /css/ references in public/*.html.

Version is the first 10 hex characters of the SHA-256 of the referenced file.
No third-party dependencies.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

# href="/css/..." or src="/js/..." with a ?v= query. External URLs are ignored.
ASSET_RE = re.compile(
    r"""((?:href|src)=["'])(/(?:css|js)/[^"'?#]+)(\?v=)([^"'#]*)(["'])""",
    re.I,
)


def file_version(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:10]


def asset_path(url_path: str) -> Path:
    rel = url_path.lstrip("/")
    return PUBLIC / rel


def rewrite_html(html: str) -> str:
    def repl(match: re.Match[str]) -> str:
        url_path = match.group(2)
        path = asset_path(url_path)
        if not path.is_file():
            raise SystemExit(f"missing asset {url_path} -> {path}")
        return f"{match.group(1)}{url_path}{match.group(3)}{file_version(path)}{match.group(5)}"

    return ASSET_RE.sub(repl, html)


def html_pages() -> list[Path]:
    return sorted(p for p in PUBLIC.glob("*.html") if p.is_file())


def main() -> int:
    changed = 0
    for page in html_pages():
        original = page.read_text(encoding="utf-8")
        updated = rewrite_html(original)
        if updated == original:
            print(f"unchanged {page.relative_to(ROOT)}")
            continue
        page.write_text(updated, encoding="utf-8")
        changed += 1
        print(f"updated {page.relative_to(ROOT)}")
    print(f"pages={len(html_pages())} rewritten={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
