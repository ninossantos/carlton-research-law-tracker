#!/usr/bin/env python3
"""Schema and house-style checks for the coercive control appeal tracker."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "appeals.json"
PUBLIC_DATA = ROOT / "public" / "data" / "appeals.json"
APPEALS_HTML = ROOT / "public" / "appeals.html"
APPEALS_JS = ROOT / "public" / "js" / "appeals.js"
INDEX = ROOT / "public" / "index.html"

REQUIRED = [
    "id",
    "state",
    "stateAbbr",
    "court",
    "title",
    "docket",
    "citation",
    "date",
    "dateSort",
    "disposition",
    "remanded",
    "summary",
    "opinionUrl",
    "source",
]

DUMMY = re.compile(
    r"\b(it is|it was|there is|there are|there was|there were|it's|there's)\b",
    re.I,
)
DASH = re.compile(r"[\u2014\u2013]")
PHRASE = re.compile(r"coercive control|controlling or coercive", re.I)
DONATE = re.compile(r"donate", re.I)
HOPEFUL = re.compile(r"hopeful child", re.I)
ORANGE = re.compile(r"#f55f0d", re.I)
BANNED_TERMS = re.compile(r"\b(codes|coding|UNCODED)\b")

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Cannot parse {path}: {exc}")
        return None


def scan_text(label: str, text: str) -> None:
    m = DUMMY.search(text or "")
    if m:
        fail(f"{label}: dummy construction {m.group(0)!r}")
    if DASH.search(text or ""):
        fail(f"{label}: em dash or en dash")
    m2 = BANNED_TERMS.search(text or "")
    if m2:
        fail(f"{label}: banned term {m2.group(0)!r}")


def main() -> int:
    a = load_json(DATA)
    b = load_json(PUBLIC_DATA)
    if a is None or b is None:
        print("\n".join(errors))
        return 1
    if a != b:
        fail("data/appeals.json and public/data/appeals.json are not identical")

    meta = a.get("meta") or {}
    scan_text("meta.title", meta.get("title", ""))
    scan_text("meta.sourceNote", meta.get("sourceNote", ""))
    method = meta.get("method")
    if not isinstance(method, list) or not method:
        fail("meta.method must be a non-empty array")
    else:
        for i, s in enumerate(method):
            scan_text(f"meta.method[{i}]", s)
        joined = " ".join(method)
        if "A published opinion that names coercive control does not finish the work." not in joined:
            fail("method must include the published-opinion sentence")
        if "The hard part is showing the pattern in a longitudinal record." not in joined:
            fail("method must include the longitudinal-record sentence")

    rows = a.get("cases")
    if not isinstance(rows, list) or not rows:
        fail("cases array missing")
        print("\n".join(errors))
        return 1

    ids = set()
    by_state: dict[str, int] = {}
    for row in rows:
        rid = row.get("id", "<no-id>")
        for key in REQUIRED:
            if key not in row:
                fail(f"{rid}: missing {key}")
        url = row.get("opinionUrl") or ""
        if not (url.startswith("http://") or url.startswith("https://")):
            fail(f"{rid}: opinionUrl must be http(s)")
        summary = row.get("summary") or ""
        if not summary.strip():
            fail(f"{rid}: summary empty")
        # Opinion language may use dummy constructions. Scan title and court only.
        scan_text(f"{rid}.title", row.get("title", ""))
        scan_text(f"{rid}.court", row.get("court", ""))
        dedicated = row.get("namedPhrase") or row.get("phrase") or ""
        if not PHRASE.search(summary) and not PHRASE.search(dedicated):
            fail(f"{rid}: summary (or named field) must name coercive control or controlling or coercive")
        if not isinstance(row.get("remanded"), bool):
            fail(f"{rid}: remanded must be boolean")
        if rid in ids:
            fail(f"duplicate id {rid}")
        ids.add(rid)
        st = row.get("state") or ""
        by_state[st] = by_state.get(st, 0) + 1

    for path in (APPEALS_HTML, APPEALS_JS, INDEX):
        if not path.is_file():
            fail(f"{path.relative_to(ROOT)} missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT)
        if DONATE.search(text):
            fail(f"{rel}: contains donate")
        if HOPEFUL.search(text):
            fail(f"{rel}: contains Hopeful Child")
        if ORANGE.search(text):
            fail(f"{rel}: contains #f55f0d")

    if APPEALS_HTML.is_file():
        html = APPEALS_HTML.read_text(encoding="utf-8")
        for needle in (
            "Carlton Research",
            "filter-state",
            "No published appellate opinion naming coercive control is in this tracker yet.",
            "Inquire about coercive control",
            "The list updates monthly",
        ):
            if needle not in html:
                fail(f"public/appeals.html missing {needle!r}")
        if "appeals.js" not in html:
            fail("public/appeals.html must load appeals.js")

    if APPEALS_JS.is_file():
        js = APPEALS_JS.read_text(encoding="utf-8")
        if "Alabama" not in js or "Wyoming" not in js or "District of Columbia" not in js:
            fail("appeals.js must list all 50 states and D.C.")
        if "cc-tracker-height" not in js:
            fail("appeals.js must postMessage height")
        if "/api/appeals" not in js:
            fail("appeals.js must fetch /api/appeals")
        if "8765" in js:
            fail("appeals.js must not mention the local dev port")

    if INDEX.is_file():
        idx = INDEX.read_text(encoding="utf-8")
        if "/appeals" not in idx and "appeals.html" not in idx:
            fail("public/index.html must link to /appeals")

    public_root = ROOT / "public"
    for path in public_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".js", ".css"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(ROOT)
            if DONATE.search(text):
                fail(f"{rel}: contains donate")
            if HOPEFUL.search(text):
                fail(f"{rel}: contains Hopeful Child")
            if ORANGE.search(text):
                fail(f"{rel}: contains #f55f0d")

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS")
    print(" cases=" + str(len(rows)) + " states=" + str(len(by_state)))
    for st in sorted(by_state):
        print(f"  {st}: {by_state[st]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
