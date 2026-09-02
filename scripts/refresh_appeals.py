#!/usr/bin/env python3
"""Harvest CourtListener opinions that use the words coercive control.

Writes data/appeals.json and public/data/appeals.json. Used by the weekly
GitHub Action so the static backup stays current when /api/appeals is down.
Keeps one published card per case and fills a summary from the opinion PDF.
"""

from __future__ import annotations

import logging
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

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
STUB_PREFIX = "Published opinion that uses the words coercive control"
NEEDLES = ("coercive control", "controlling or coercive")
UA = "CarltonResearchTracker/1.0 (https://tracker.carltonresearch.com/; weekly harvest)"


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


def docket_base(docket: str) -> str:
    s = re.sub(r"\s+", "", str(docket or "").upper())
    s = re.sub(r"[–—]", "-", s)
    s = s.split("/")[0]
    s = re.sub(r"REL$", "", s)
    s = re.sub(r"-(I|II|III|IV|V)$", "", s)
    if re.search(r"\d[A-Z]$", s):
        s = s[:-1]
    return s


def title_key(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", str(title or "").lower())
    s = re.sub(r"\b(v|vs|and)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def case_key(row: dict) -> str:
    base = docket_base(row.get("docket") or "")
    abbr = row.get("stateAbbr") or ""
    if len(base) >= 4:
        return f"{abbr}|d|{base}"
    return f"{abbr}|t|{title_key(row.get('title') or '')}|{row.get('dateSort') or ''}"


def is_published(row: dict) -> bool:
    return str(row.get("status") or "").lower() in {"published", "precedential"}


def is_stub(summary: str) -> bool:
    s = (summary or "").strip()
    if not s:
        return True
    if s.startswith(STUB_PREFIX):
        return True
    if s.startswith("The court names coercive control"):
        return True
    return not any(n in s.lower() for n in NEEDLES)


def rank(row: dict) -> int:
    n = 0
    if is_published(row):
        n += 50
    if not is_stub(row.get("summary") or ""):
        n += 40
    if row.get("source") == "official PDF":
        n += 15
    n += min(20, len(row.get("docket") or ""))
    n += min(10, len(row.get("summary") or "") // 80)
    return n


def merge_row(a: dict, b: dict) -> dict:
    win, lose = (a, b) if rank(a) >= rank(b) else (b, a)
    out = dict(lose)
    out.update(win)
    if is_stub(win.get("summary") or "") and not is_stub(lose.get("summary") or ""):
        out["summary"] = lose["summary"]
        if lose.get("disposition"):
            out["disposition"] = lose["disposition"]
        if lose.get("remanded"):
            out["remanded"] = lose["remanded"]
    if not is_published(win) and is_published(lose):
        out["status"] = lose.get("status") or out.get("status")
    if win.get("source") != "official PDF" and lose.get("source") == "official PDF":
        out["opinionUrl"] = lose.get("opinionUrl") or out.get("opinionUrl")
        out["source"] = "official PDF"
    if not out.get("citation") and lose.get("citation"):
        out["citation"] = lose["citation"]
    return out


def uniquify_ids(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    for row in rows:
        rid = str(row.get("id") or "")
        if not rid or rid in seen:
            row["id"] = slug(f"{row.get('stateAbbr')}-{row.get('docket')}-{row.get('dateSort')}")
        seen.add(row["id"])
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        key = case_key(row)
        if key not in best:
            best[key] = row
            order.append(key)
        else:
            best[key] = merge_row(best[key], row)
    return [best[k] for k in order]


def load_seed():
    if not DATA.is_file():
        return []
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    return payload.get("cases") or []


def fetch_page(url: str, token: str) -> dict:
    headers = {"Accept": "application/json", "User-Agent": UA}
    if token:
        headers["Authorization"] = "Token " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("\u2014", ", ").replace("\u2013", ", ")
    return re.sub(r"\s+", " ", s).strip()


def excerpt_from_text(text: str) -> str:
    blob = strip_html(text)
    if not blob:
        return ""
    low = blob.lower()
    idx = -1
    for n in NEEDLES:
        idx = low.find(n)
        if idx >= 0:
            break
    if idx < 0:
        return ""
    sents = re.split(r"(?<=[.!?])\s+", blob)
    preferred = []
    first = []
    for i, sent in enumerate(sents):
        if not any(n in sent.lower() for n in NEEDLES):
            continue
        keep = []
        if i and len(sent) < 140:
            keep.append(sents[i - 1])
        keep.append(sent)
        if i + 1 < len(sents) and len(sent) < 220:
            keep.append(sents[i + 1])
        joined = " ".join(keep).strip()
        if any(n in joined.lower() for n in NEEDLES):
            if not first:
                first = [joined]
            if re.search(r"\b(found|held|affirmed|reversed|concluded|remanded)\b", joined, re.I):
                preferred.append(joined)
                break
    out = (preferred or first or [""])[0]
    if not out or not any(n in out.lower() for n in NEEDLES):
        start = max(0, idx - 180)
        end = min(len(blob), idx + 400)
        out = blob[start:end].strip()
        if start:
            out = out.split(" ", 1)[-1]
        if end < len(blob):
            out = out.rsplit(" ", 1)[0]
    out = out.replace("\u2014", ", ").replace("\u2013", ", ")
    if len(out) > 900:
        cut = out[:897]
        out = (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(",;") + "."
    if not any(n in out.lower() for n in NEEDLES):
        return ""
    return out


def pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for i, page in enumerate(reader.pages[:30]):
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
        blob = " ".join(parts)
        if i >= 1 and any(n in blob.lower() for n in NEEDLES):
            break
    return " ".join(parts)


def fetch_bytes(url: str) -> bytes | None:
    if not url:
        return None
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


_PDF_CACHE: dict[str, str] = {}


def pdf_excerpt(local_path: str, download_url: str) -> str:
    key = local_path or download_url
    if key in _PDF_CACHE:
        return _PDF_CACHE[key]
    urls = []
    if local_path:
        urls.append("https://storage.courtlistener.com/" + local_path.lstrip("/"))
    if download_url and download_url.startswith("http"):
        urls.append(download_url)
    for url in urls:
        data = fetch_bytes(url)
        if not data:
            continue
        if data.startswith(b"%PDF"):
            try:
                text = pdf_text(data)
            except Exception:
                continue
            excerpt = excerpt_from_text(text)
            if excerpt:
                _PDF_CACHE[key] = excerpt
                time.sleep(0.25)
                return excerpt
            continue
        try:
            html = data.decode("utf-8", "replace")
        except Exception:
            continue
        excerpt = excerpt_from_text(html)
        if excerpt:
            _PDF_CACHE[key] = excerpt
            time.sleep(0.2)
            return excerpt
    _PDF_CACHE[key] = ""
    return ""


def seed_match(hit: dict, by_docket: dict, by_docket_base: dict, by_title: dict):
    docket = hit.get("docketNumber") or ""
    title = hit.get("caseName") or ""
    compact = docket.replace(" ", "")
    if compact and compact in by_docket:
        return by_docket[compact]
    base = docket_base(docket)
    if len(base) >= 4 and base in by_docket_base:
        return by_docket_base[base]
    return by_title.get(title.lower()) or by_title.get(title_key(title))


def map_hit(hit: dict, seed_row: dict | None) -> dict:
    place = place_for(hit)
    state_name, abbr = place
    docket = hit.get("docketNumber") or ""
    title = hit.get("caseName") or "Untitled opinion"
    iso = hit.get("dateFiled") or ""
    cites = hit.get("citation") or hit.get("neutralCite") or ""
    if isinstance(cites, list):
        cites = "; ".join(cites)
    path = hit.get("absolute_url") or ""
    live_url = path if str(path).startswith("http") else ("https://www.courtlistener.com" + path if path else "")
    ops = hit.get("opinions") or [{}]
    op0 = ops[0] if ops else {}
    snippet = strip_html((hit.get("snippet") or "") + " " + (op0.get("snippet") or ""))
    syllabus = strip_html(hit.get("syllabus") or "")
    local_path = op0.get("local_path") or ""
    download_url = op0.get("download_url") or live_url

    if seed_row and not is_stub(seed_row.get("summary") or ""):
        summary = seed_row.get("summary") or ""
        opinion_url = seed_row.get("opinionUrl") if seed_row.get("source") == "official PDF" else (download_url or live_url)
        source = seed_row.get("source") if seed_row.get("source") == "official PDF" else "CourtListener"
        disposition = seed_row.get("disposition") or ""
        remanded = bool(seed_row.get("remanded"))
        rid = seed_row.get("id") or slug(f"{hit.get('court_id')}-{docket}-{iso}")
        citation = seed_row.get("citation") or cites
    else:
        summary = syllabus or (snippet if any(n in snippet.lower() for n in NEEDLES) else "")
        opinion_url = download_url or live_url
        source = "CourtListener"
        disposition = (seed_row or {}).get("disposition") or ""
        remanded = bool((seed_row or {}).get("remanded"))
        rid = slug(f"{hit.get('court_id')}-{docket}-{iso}")
        citation = cites
        if local_path:
            fetched = pdf_excerpt(local_path, download_url)
            if fetched:
                summary = fetched
        if is_stub(summary):
            summary = (
                "The court names coercive control in this opinion. "
                "Open the opinion to read the passage that uses the term."
            )

    return {
        "id": rid,
        "state": state_name,
        "stateAbbr": abbr,
        "court": hit.get("court") or (seed_row or {}).get("court") or "",
        "title": title,
        "docket": docket,
        "citation": citation,
        "date": format_date(iso),
        "dateSort": iso,
        "disposition": disposition,
        "remanded": remanded,
        "summary": summary,
        "opinionUrl": opinion_url,
        "source": source,
        "status": hit.get("status") or "",
    }


def harvest(token: str) -> list[dict]:
    seed = load_seed()
    by_docket = {str(r.get("docket") or "").replace(" ", ""): r for r in seed if r.get("docket")}
    by_docket_base = {}
    for r in seed:
        base = docket_base(r.get("docket") or "")
        if len(base) >= 4:
            by_docket_base[base] = r
    by_title = {}
    for r in seed:
        if r.get("title"):
            by_title[str(r["title"]).lower()] = r
            by_title[title_key(r["title"])] = r

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
            if not place_for(hit):
                continue
            collected.append(map_hit(hit, seed_match(hit, by_docket, by_docket_base, by_title)))
        url = body.get("next") or ""
        if url:
            time.sleep(1.0)

    combined = collected + seed
    rows = uniquify_ids(dedupe(combined))
    return [
        r
        for r in rows
        if any(n in (r.get("summary") or "").lower() for n in NEEDLES)
        and not (r.get("summary") or "").startswith("The court names coercive control")
        and not (r.get("summary") or "").startswith(STUB_PREFIX)
    ]


def main() -> int:
    token = os.environ.get("COURTLISTENER_TOKEN", "")
    cases = harvest(token)
    payload = {
        "meta": {
            "title": "Coercive Control Appeal Tracker",
            "lastUpdated": today_stamp(),
            "sourceNote": (
                "CourtListener search of United States opinions that use the words coercive control. "
                "The list keeps one published card per case. Research, not legal advice."
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
