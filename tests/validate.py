#!/usr/bin/env python3
"""Schema and lock checks for the named-term tracker."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "instruments.json"
PUBLIC_DATA = ROOT / "public" / "data" / "instruments.json"
INDEX = ROOT / "public" / "index.html"
BILLS_FN = ROOT / "functions" / "api" / "bills.js"

REQUIRED = [
    "id",
    "geographyType",
    "jurisdiction",
    "jurisdictionCode",
    "instrument",
    "citation",
    "status",
    "domain",
    "accomplishes",
    "date",
    "dateSort",
    "sourceUrl",
    "namedTerm",
    "scored",
]
GEO = {"us-state", "country", "us-federal"}
STATUS = {"in-force", "pipeline", "enacted-not-commenced", "not-scored"}
DOMAIN = {"criminal", "civil-protective-order", "custody", "definitional"}
LOCKED_US = {
    "Arizona",
    "California",
    "Colorado",
    "Connecticut",
    "Hawaii",
    "Massachusetts",
    "New Hampshire",
    "New Jersey",
    "Oklahoma",
    "Utah",
    "Vermont",
    "Washington",
}
DUMMY = re.compile(
    r"\b(it is|it was|there is|there are|there was|there were|it's|there's)\b",
    re.I,
)
DASH = re.compile(r"[\u2014\u2013]")
BANNED_TERMS = re.compile(r"\b(codes|coding|UNCODED)\b")
KEY_PAT = re.compile(r"(OPENSTATES_API_KEY|api[_-]?key\s*[:=]|sk-[A-Za-z0-9]{8,})", re.I)
DONATE = re.compile(r"donate", re.I)
HOPEFUL = re.compile(r"hopeful child", re.I)
ORANGE = re.compile(r"#f55f0d", re.I)
OPENSTATES_TOKEN = re.compile(r"OPENSTATES")

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Cannot parse {path}: {exc}")
        return None


def scan_text(label: str, text: str, extra_bans: bool = False) -> None:
    m = DUMMY.search(text)
    if m:
        fail(f"{label}: dummy construction {m.group(0)!r}")
    if DASH.search(text):
        fail(f"{label}: em dash or en dash")
    if extra_bans:
        m2 = BANNED_TERMS.search(text)
        if m2:
            fail(f"{label}: banned term {m2.group(0)!r}")


def main() -> int:
    a = load_json(DATA)
    b = load_json(PUBLIC_DATA)
    if a is None or b is None:
        print("\n".join(errors))
        return 1
    if a != b:
        fail("data/instruments.json and public/data/instruments.json are not identical")

    if a.get("lastUpdated") != "August 31, 2026":
        fail("lastUpdated must be August 31, 2026")

    method = a.get("method")
    if not isinstance(method, list) or len(method) != 5:
        fail("method must be an array of 5 sentences")
    else:
        for i, s in enumerate(method):
            scan_text(f"method[{i}]", s)

    usa = a.get("usaTodayErrors", "")
    scan_text("usaTodayErrors", usa)

    rows = a.get("instruments")
    if not isinstance(rows, list) or not rows:
        fail("instruments array missing")
        print("\n".join(errors))
        return 1

    ids = set()
    us_inf = set()
    for row in rows:
        rid = row.get("id", "<no-id>")
        for key in REQUIRED:
            if key not in row:
                fail(f"{rid}: missing {key}")
        if row.get("geographyType") not in GEO:
            fail(f"{rid}: bad geographyType")
        if row.get("status") not in STATUS:
            fail(f"{rid}: bad status")
        if row.get("domain") not in DOMAIN:
            fail(f"{rid}: bad domain")
        if not isinstance(row.get("namedTerm"), bool) or not isinstance(row.get("scored"), bool):
            fail(f"{rid}: namedTerm/scored must be boolean")
        scan_text(f"{rid}.accomplishes", row.get("accomplishes", ""), extra_bans=True)
        if row.get("notes"):
            scan_text(f"{rid}.notes", row["notes"], extra_bans=True)
        if rid in ids:
            fail(f"duplicate id {rid}")
        ids.add(rid)
        if (
            row.get("geographyType") == "us-state"
            and row.get("status") == "in-force"
            and row.get("namedTerm") is True
        ):
            us_inf.add(row.get("jurisdiction"))

    if us_inf != LOCKED_US:
        fail(f"US in-force named-term states {sorted(us_inf)} != locked {sorted(LOCKED_US)}")
    if len(us_inf) != 12:
        fail(f"unique in-force US states == {len(us_inf)}, expected 12")

    hi = [r for r in rows if r.get("jurisdiction") == "Hawaii" and r.get("status") == "in-force"]
    hi_domains = {r.get("domain") for r in hi}
    if "criminal" not in hi_domains or "civil-protective-order" not in hi_domains:
        fail("Hawaii must appear in criminal and civil-protective-order in-force rows")

    for banned_j in ("Scotland", "Northern Ireland"):
        for r in rows:
            if r.get("jurisdiction") == banned_j and r.get("status") == "in-force" and r.get("namedTerm") is True:
                fail(f"{banned_j} must not be scored as named-term in-force")

    public_files = []
    public_root = ROOT / "public"
    for path in public_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".js", ".css"}:
            public_files.append(path)
    for path in public_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT)
        if OPENSTATES_TOKEN.search(text):
            fail(f"{rel}: contains OPENSTATES")
        if KEY_PAT.search(text):
            fail(f"{rel}: looks like an API key pattern")
        if DONATE.search(text):
            fail(f"{rel}: contains donate")
        if HOPEFUL.search(text):
            fail(f"{rel}: contains Hopeful Child")
        if ORANGE.search(text):
            fail(f"{rel}: contains #f55f0d")

    if not BILLS_FN.is_file():
        fail("functions/api/bills.js missing")
    else:
        fn = BILLS_FN.read_text(encoding="utf-8")
        if "context.env" not in fn:
            fail("functions/api/bills.js must read the key from context.env")
        if "OPENSTATES_API_KEY" not in fn:
            fail("functions/api/bills.js must reference OPENSTATES_API_KEY on context.env")

    html = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
    if not INDEX.is_file():
        fail("public/index.html missing")
    else:
        for needle in ("Carlton Research", "named-term", "August 31, 2026", "Inquire about coercive control"):
            if needle.lower() not in html.lower() and needle not in html:
                # named-term appears as Named-Term; check casefold
                if needle.casefold() not in html.casefold():
                    fail(f"public/index.html missing {needle!r}")
        if "https://carltonresearch.com/" not in html:
            fail("public/index.html missing inquire link to https://carltonresearch.com/")

    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS")
    print(f" rows={len(rows)} us_in_force_states={len(us_inf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
