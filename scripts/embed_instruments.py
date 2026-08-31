#!/usr/bin/env python3
"""Write public/js/instruments-data.js from public/data/instruments.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "public" / "data" / "instruments.json"
DST = ROOT / "public" / "js" / "instruments-data.js"


def main() -> int:
    raw = SRC.read_text(encoding="utf-8")
    payload = json.loads(raw)
    rows = payload.get("instruments")
    if not isinstance(rows, list):
        print("instruments array missing", file=sys.stderr)
        return 1
    body = raw.strip()
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text("window.CC_INSTRUMENTS = " + body + ";\n", encoding="utf-8")
    print(f"wrote {DST.relative_to(ROOT)} instruments={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
