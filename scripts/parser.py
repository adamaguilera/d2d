#!/usr/bin/env python3
"""
Parse all Dotabuff counters snapshots in a date folder and emit per-hero JSON.

Input (folder):
  ./snapshot/<YYYY-MM-DD>/

Each HTML file should be named <slug>.html, e.g.:
  ./snapshot/2025-08-28/pudge.html

Output (per hero):
  ./counter/<YYYY-MM-DD>/<slug>.json

JSON shape:
{
  "hero": "<slug>",
  "date": "YYYY-MM-DD",
  "matchups": [
    {"opponent": "<slug>", "winrate": 56.31, "disadvantage": -3.11, "matches": 153542},
    ...
  ]
}

Notes:
- Opponent slugs are pulled from the hero link in the table when available;
  otherwise we slugify the text.
- The script logs errors but keeps going (fail-open).
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup  # pip install beautifulsoup4

PCT_RE = re.compile(r"-?\d+(?:\.\d+)?")


def slugify(name: str) -> str:
    """
    Convert a visible hero name to a Dotabuff-like slug:
    - lowercase
    - replace any non-alphanumeric with hyphens
    - collapse repeated hyphens and trim
    """
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def pct_to_float(s: str) -> float:
    if s is None:
        return float("nan")
    m = PCT_RE.search(s)
    return float(m.group(0)) if m else float("nan")


def int_from_commas(s: str) -> int:
    if not s:
        return 0
    return int(re.sub(r"[^\d]", "", s))


def find_matchups_table(soup: BeautifulSoup) -> Optional[Any]:
    """
    Try multiple strategies to find the 'Matchups' table.
    """
    # Strategy 1: a <header>Matchups</header> followed by a table
    for h in soup.find_all("header"):
        if h.get_text(strip=True).lower() == "matchups":
            t = h.find_next("table")
            if t:
                return t

    # Strategy 2: any sortable table with 'win rate' in the header
    for t in soup.select("table.sortable"):
        thead_text = t.thead.get_text(
            " ", strip=True).lower() if t.thead else ""
        if "win rate" in thead_text:
            return t

    # Strategy 3: fallback to first table
    return soup.find("table")


def parse_matchups(table: Any) -> List[Dict[str, Any]]:
    """
    Parse rows, trying to extract opponent slug from the <a href="/heroes/<slug>"> if present.
    Expected columns:
      [icon], [opponent], [disadvantage], [<hero> win rate], [matches]
    """
    rows_out: List[Dict[str, Any]] = []
    tb = table.tbody or table
    for tr in tb.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue

        # Opponent slug: prefer the href; fallback to slugify cell text
        opp_slug = None
        a = tds[1].find("a", href=True)
        if a and a["href"].startswith("/heroes/"):
            tail = a["href"].split("/heroes/", 1)[1]
            parts = [p for p in tail.split("/") if p]
            if parts:
                opp_slug = parts[0].strip().lower()
        if not opp_slug:
            opp_slug = slugify(tds[1].get_text(" ", strip=True))

        # Numeric fields (use data-value when present)
        disadv_val = tds[2].get("data-value") or tds[2].get_text(strip=True)
        winrate_val = tds[3].get("data-value") or tds[3].get_text(strip=True)
        matches_val = tds[4].get("data-value") or tds[4].get_text(strip=True)

        # Some pages store disadvantage as raw float (e.g., -3.11), others as "%".
        try:
            disadvantage = float(str(disadv_val))
        except ValueError:
            disadvantage = pct_to_float(str(disadv_val))

        try:
            winrate = float(str(winrate_val))
        except ValueError:
            winrate = pct_to_float(str(winrate_val))

        matches = int_from_commas(str(matches_val))

        rows_out.append(
            {
                "opponent": opp_slug,      # ensure slug format
                "winrate": winrate,        # <hero> win rate vs opponent
                "disadvantage": disadvantage,
                "matches": matches,
            }
        )
    return rows_out


def parse_single_file(html_path: Path, hero_slug: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_path.read_text(
        encoding="utf-8", errors="ignore"), "html.parser")
    table = find_matchups_table(soup)
    if not table:
        raise RuntimeError("Matchups table not found")
    return parse_matchups(table)


def main():
    ap = argparse.ArgumentParser(
        description="Parse Dotabuff counters snapshots for a whole date folder.")
    ap.add_argument("--input-dir", required=True,
                    help="Path like ./content/snapshot/2025-08-28/")
    ap.add_argument("--out-root", default="content/counter",
                    help="Output root (default: ./content/counter)")
    ap.add_argument("--glob", default="*.html",
                    help="File pattern (default: *.html)")
    ap.add_argument("--patch", default="7.XX",
                    help="Dota patch label to record in metadata.json (default: 7.XX)")
    args = ap.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Not a directory: {input_dir}")

    date_str = input_dir.name  # expect folder name is the date
    out_dir = Path(args.out_root) / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_dir.glob(args.glob))
    if not html_files:
        raise SystemExit(f"No HTML files matching {args.glob} in {input_dir}")

    successes, failures = 0, 0

    for html_path in html_files:
        # Hero slug is the file stem (e.g., pudge.html -> pudge)
        hero_slug = html_path.stem.lower()

        try:
            matchups = parse_single_file(html_path, hero_slug)
            payload = {
                "hero": hero_slug,  # ensure hero name conforms to slug
                "date": date_str,
                "matchups": matchups,
            }
            out_path = out_dir / f"{hero_slug}.json"
            out_path.write_text(json.dumps(
                payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Saved {out_path}")
            successes += 1
        except Exception as e:
            print(f"ERROR parsing {html_path.name} ({hero_slug}): {e}")
            failures += 1
            continue

    print("\n=== Summary ===")
    print(f"Parsed OK: {successes}")
    print(f"Failed:   {failures}")

    # Write metadata.json for the date folder
    meta = {
        "date": date_str,
        "patch": args.patch or "7.XX",
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {(out_dir / 'metadata.json')}")


if __name__ == "__main__":
    main()
