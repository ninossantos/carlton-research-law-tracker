#!/usr/bin/env python3
"""Harvest CourtListener opinions that use the words coercive control.

Writes data/appeals.json and public/data/appeals.json. Used by the weekly
GitHub Action so the static backup stays current when /api/appeals is down.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "appeals.json"
PUBLIC = ROOT / "public" / "data" / "appeals.json"

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

FEDERAL_IDS = {
    "scotus", "ca1", "ca2", "ca3", "ca4", "ca5", "ca6", "ca7",
    "ca8", "ca9", "ca10", "ca11", "cadc", "cafc", "ccpa",
}

COURT_STATE = {
    "ala": "AL", "alactapp": "AL", "alacrimapp": "AL", "alcivapp": "AL",
    "alaska": "AK", "alaskactapp": "AK",
    "ariz": "AZ", "arizctapp": "AZ",
    "ark": "AR", "arkctapp": "AR",
    "cal": "CA", "calctapp": "CA",
    "colo": "CO", "coloctapp": "CO",
    "conn": "CT", "connappct": "CT",
    "del": "DE",
    "dc": "DC", "dcappeals": "DC",
    "fla": "FL", "fladistctapp": "FL",
    "ga": "GA", "gactapp": "GA",
    "haw": "HI", "hawapp": "HI",
    "idaho": "ID",
    "ill": "IL", "illappct": "IL",
    "ind": "IN", "indctapp": "IN",
    "iowa": "IA", "iowactapp": "IA",
    "kan": "KS", "kanctapp": "KS",
    "ky": "KY", "kyctapp": "KY",
    "la": "LA", "lactapp": "LA",
    "me": "ME",
    "md": "MD", "mdctspecapp": "MD", "mdctapp": "MD",
    "mass": "MA", "massappct": "MA",
    "mich": "MI", "michctapp": "MI",
    "minn": "MN", "minnctapp": "MN",
    "miss": "MS", "missctapp": "MS",
    "mo": "MO", "moctapp": "MO",
    "mont": "MT",
    "neb": "NE", "nebctapp": "NE",
    "nev": "NV",
    "nh": "NH",
    "nj": "NJ", "njsuperctappdiv": "NJ",
    "nm": "NM", "nmctapp": "NM",
    "ny": "NY", "nyappdiv": "NY", "nyappterm": "NY",
    "nc": "NC", "ncctapp": "NC",
    "nd": "ND",
    "ohio": "OH", "ohioctapp": "OH",
    "okla": "OK", "oklacivapp": "OK", "oklacrimapp": "OK",
    "or": "OR", "orctapp": "OR",
    "pa": "PA", "pasuperct": "PA", "pacommwct": "PA",
    "ri": "RI",
    "sc": "SC", "scctapp": "SC",
    "sd": "SD",
    "tenn": "TN", "tennctapp": "TN", "tenncrimapp": "TN",
    "tex": "TX", "texapp": "TX", "texcrimapp": "TX",
    "utah": "UT", "utahctapp": "UT",
    "vt": "VT",
    "va": "VA", "vactapp": "VA",
    "wash": "WA", "washctapp": "WA",
    "wva": "WV",
    "wis": "WI", "wisctapp": "WI",
    "wyo": "WY",
}

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

NAME_TO_ABBR = {name.lower(): abbr for abbr, name in STATE_NAMES.items()}


def format_date(iso: str) -> str:
    if not iso or len(iso) < 10:
        return iso or ""
    y, m, d = iso[:4], int(iso[5:7]), int(iso[8:10])
    if m < 1 or m > 12:
        return iso
    return f"{MONTHS[m - 1]} {d}, {y}"


def today_stamp() -> str:
    n = date.today()
    return f"{MONTHS[n.month - 1]} {n.day}, {n.year}"


def place_for(hit: dict):
    cid = hit.get("court_id") or ""
    if cid in FEDERAL_IDS or (len(cid) <= 4 and cid.startswith("ca") and cid[2:].isdigit()):
        return "Federal", "US"
    if cid in COURT_STATE:
        abbr = COURT_STATE[cid]
        return STATE_NAMES[abbr], abbr
    court = (hit.get("court") or "").lower()
    for name, abbr in NAME_TO_ABBR.items():
        if name in court:
            return STATE_NAMES[abbr], abbr
    return None


def slug(s: str) -> str:
    out = []
    for ch in (s or "").lower():
        if ch.isalnum():
            out.append(ch)
        else:
            if not out or out[-1] != "-":
                out.append("-")
    return "".join(out).strip("-")[:80]


def load_seed():
    if not DATA.is_file():
        return []
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    return payload.get("cases") or []


def fetch_page(url: str, token: str) -> dict:
    headers = {
        "Accept": "application/json",
        "User-Agent": "CarltonResearchTracker/1.0 (https://tracker.carltonresearch.com/; weekly harvest)",
    }
    if token:
        headers["Authorization"] = "Token " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def harvest(token: str) -> list[dict]:
    seed = load_seed()
    by_docket = {str(r.get("docket") or "").replace(" ", ""): r for r in seed if r.get("docket")}
    by_title = {str(r.get("title") or "").lower(): r for r in seed if r.get("title")}
    url = (
        "https://www.courtlistener.com/api/rest/v4/search/"
        "?q=%22coercive%20control%22&type=o&order_by=dateFiled%20desc"
    )
    collected = []
    pages = 0
    while url and pages < 10:
        pages += 1
        body = fetch_page(url, token)
        for hit in body.get("results") or []:
            place = place_for(hit)
            if not place:
                continue
            state_name, abbr = place
            docket = hit.get("docketNumber") or ""
            title = hit.get("caseName") or "Untitled opinion"
            seed_row = by_docket.get(docket.replace(" ", "")) or by_title.get(title.lower())
            iso = hit.get("dateFiled") or ""
            cites = hit.get("citation") or hit.get("neutralCite") or ""
            if isinstance(cites, list):
                cites = "; ".join(cites)
            path = hit.get("absolute_url") or ""
            live_url = path if path.startswith("http") else ("https://www.courtlistener.com" + path if path else "")
            syllabus = " ".join((hit.get("syllabus") or "").split()).strip()
            if seed_row:
                summary = seed_row.get("summary") or ""
                opinion_url = seed_row.get("opinionUrl") if seed_row.get("source") == "official PDF" else live_url
                source = seed_row.get("source") if seed_row.get("source") == "official PDF" else "CourtListener"
                disposition = seed_row.get("disposition") or ""
                remanded = bool(seed_row.get("remanded"))
                rid = seed_row.get("id")
            else:
                summary = syllabus[:900] if syllabus else (
                    "Published opinion that uses the words coercive control. Read the full opinion."
                )
                opinion_url = live_url
                source = "CourtListener"
                disposition = ""
                remanded = False
                rid = slug(f"{hit.get('court_id')}-{docket}-{iso}")
            collected.append({
                "id": rid,
                "state": state_name,
                "stateAbbr": abbr,
                "court": hit.get("court") or "",
                "title": title,
                "docket": docket,
                "citation": (seed_row.get("citation") if seed_row and seed_row.get("citation") else cites),
                "date": format_date(iso),
                "dateSort": iso,
                "disposition": disposition,
                "remanded": remanded,
                "summary": summary,
                "opinionUrl": opinion_url,
                "source": source,
                "status": hit.get("status") or "",
            })
        url = body.get("next") or ""
        if url:
            time.sleep(1.2)
    seen = set()
    out = []
    for row in collected:
        key = f"{row.get('docket') or row.get('title')}|{row.get('dateSort')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    for row in seed:
        key = f"{row.get('docket') or row.get('title')}|{row.get('dateSort') or ''}"
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def main() -> int:
    token = os.environ.get("COURTLISTENER_TOKEN", "")
    cases = harvest(token)
    payload = {
        "meta": {
            "title": "Coercive Control Appeal Tracker",
            "lastUpdated": today_stamp(),
            "sourceNote": (
                "CourtListener search of United States opinions that use the words coercive control. "
                "The list updates automatically. Research, not legal advice."
            ),
            "method": [
                "A published opinion that names coercive control does not finish the work.",
                "The hard part is showing the pattern in a longitudinal record.",
                "Research, not legal advice.",
                "Carlton Research, LLC does not represent parties and does not make parenting-time recommendations.",
                "CourtListener supplies the list. The list updates automatically.",
            ],
            "live": True,
            "count": len(cases),
        },
        "cases": cases,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    DATA.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(text, encoding="utf-8")
    PUBLIC.write_text(text, encoding="utf-8")
    print(f"wrote {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
