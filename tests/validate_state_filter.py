#!/usr/bin/env python3
"""State-filter normalization for the coercive control appeal tracker.

Mirrors public/js/appeals.js and functions/api/appeals.js:
trim and uppercase stateAbbr; if that code is missing or not a US state
or US, derive it from the state name (case- and whitespace-insensitive)
via US_STATES, with Federal mapping to US.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "public" / "data" / "appeals.json"

US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("DC", "District of Columbia"), ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"),
    ("ID", "Idaho"), ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"),
    ("KS", "Kansas"), ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"),
    ("MD", "Maryland"), ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"),
    ("MS", "Mississippi"), ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"),
    ("NV", "Nevada"), ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"),
    ("NY", "New York"), ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"),
    ("OK", "Oklahoma"), ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"),
    ("SC", "South Carolina"), ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"),
    ("UT", "Utah"), ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"),
    ("WV", "West Virginia"), ("WI", "Wisconsin"), ("WY", "Wyoming"),
]

ABBR_OK = {abbr: True for abbr, _name in US_STATES}
ABBR_OK["US"] = True
NAME_TO_ABBR = {"federal": "US"}
for abbr, name in US_STATES:
    NAME_TO_ABBR["".join(name.lower().split())] = abbr

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def normalized_state_code(case: dict) -> str:
    raw = str(case.get("stateAbbr") or "").strip().upper()
    if raw and ABBR_OK.get(raw):
        return raw
    name = "".join(str(case.get("state") or "").lower().split())
    if name in NAME_TO_ABBR:
        return NAME_TO_ABBR[name]
    return raw


def selected(cases: list[dict], state_filter: str) -> list[dict]:
    if state_filter == "all":
        return list(cases)
    return [case for case in cases if normalized_state_code(case) == state_filter]


def check_rules() -> None:
    samples = [
        ({"stateAbbr": " ny ", "state": "Somewhere"}, "NY"),
        ({"stateAbbr": "", "state": "new york"}, "NY"),
        ({"stateAbbr": "N.Y.", "state": "New York"}, "NY"),
        ({"stateAbbr": "  ", "state": "  District   of Columbia "}, "DC"),
        ({"stateAbbr": "", "state": "Federal"}, "US"),
        ({"stateAbbr": "us", "state": "Federal"}, "US"),
        ({"stateAbbr": "ca", "state": "New York"}, "CA"),
        ({"stateAbbr": "xx", "state": "California"}, "CA"),
        ({"stateAbbr": "NEW YORK", "state": "New York"}, "NY"),
    ]
    for case, expected in samples:
        got = normalized_state_code(case)
        if got != expected:
            fail(f"rule {case!r}: expected {expected}, got {got}")


def main() -> int:
    check_rules()
    try:
        payload = json.loads(DATA.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Cannot parse {DATA}: {exc}")
        print("FAIL")
        for err in errors:
            print(" -", err)
        return 1

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        fail("public/data/appeals.json has no cases")
        print("FAIL")
        for err in errors:
            print(" -", err)
        return 1

    all_rows = selected(cases, "all")
    if len(all_rows) != len(cases):
        fail("All states dropped cases")

    codes_in_data = sorted({normalized_state_code(case) for case in cases})
    for code in codes_in_data:
        if code == "US" or code not in ABBR_OK:
            continue
        filtered_count = len(selected(cases, code))
        in_all = sum(1 for case in all_rows if normalized_state_code(case) == code)
        if filtered_count != in_all:
            fail(f"{code}: filtered {filtered_count} != {in_all} in All states")
        if filtered_count == 0:
            fail(f"{code}: state is in the data but the filter returns 0")

    for case in cases:
        code = normalized_state_code(case)
        if code == "US":
            continue
        if code not in ABBR_OK or code == "US":
            fail(
                f"{case.get('id')}: non-US case maps to {code!r}, "
                f"not a US_STATES code (state={case.get('state')!r}, "
                f"stateAbbr={case.get('stateAbbr')!r})"
            )

    ny_rows = selected(cases, "NY")
    farq = [
        case for case in ny_rows
        if str(case.get("title") or "").strip().lower() == "people v. farquharson"
    ]
    if not farq:
        fail("NY filter does not include People v. Farquharson")
    else:
        in_all_titles = {str(case.get("title") or "") for case in all_rows}
        if "People v. Farquharson" not in in_all_titles:
            fail("All states is missing People v. Farquharson")

    if errors:
        print("FAIL")
        for err in errors:
            print(" -", err)
        return 1
    print("PASS")
    print(f" cases={len(cases)} states={len([c for c in codes_in_data if c != 'US'])} ny={len(ny_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
