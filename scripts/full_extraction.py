#!/usr/bin/env python3
"""
Unified full extraction script:
- Discovers Dotabuff hero slugs
- Fetches in-memory HTML snapshots for each hero's counters page
- Parses the Matchups table into structured JSON
- Saves per-hero results to ../content/matchups/<PATCH>/<hero>.json
- Writes metadata.json with updated_at and patch

Differences from extractor.py + parser.py:
- Does NOT persist raw HTML snapshots to disk; uses in-memory HTML
- Uses robust retry logic per hero (up to --retries with --retry-sleep seconds)

Defaults:
- Patch is auto-detected from dota2.com (can be overridden via --patch)
"""

import argparse
import datetime as dt
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup  # pip install beautifulsoup4

# Reuse browser automation utilities from extractor.py
try:
    from extractor import (
        build_driver,
        extract_hero_slugs,
        wait_for_matchups_table,
    )
    from selenium.common.exceptions import WebDriverException, TimeoutException
except Exception as import_err:  # pragma: no cover - safety for runtime envs
    print(
        f"ERROR importing selenium/extractor helpers: {import_err}", file=sys.stderr)
    raise


# -----------------------------
# Parser helpers (adapted from parser.py)
# -----------------------------
import re

PCT_RE = re.compile(r"-?\d+(?:\.\d+)?")


def slugify(name: str) -> str:
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
    # Strategy 1: a <header>Matchups</header> followed by a table
    for h in soup.find_all("header"):
        if h.get_text(strip=True).lower() == "matchups":
            t = h.find_next("table")
            if t is not None:
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
    rows_out: List[Dict[str, Any]] = []
    tb = table.tbody or table
    for tr in tb.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue

        opp_slug: Optional[str] = None
        a = tds[1].find("a", href=True)
        if a and str(a.get("href", "")).startswith("/heroes/"):
            tail = str(a["href"]).split("/heroes/", 1)[1]
            parts = [p for p in tail.split("/") if p]
            if parts:
                opp_slug = parts[0].strip().lower()
        if not opp_slug:
            opp_slug = slugify(tds[1].get_text(" ", strip=True))

        disadv_val = tds[2].get("data-value") or tds[2].get_text(strip=True)
        winrate_val = tds[3].get("data-value") or tds[3].get_text(strip=True)
        matches_val = tds[4].get("data-value") or tds[4].get_text(strip=True)

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
                "opponent": opp_slug,
                "winrate": winrate,
                "disadvantage": disadvantage,
                "matches": matches,
            }
        )
    return rows_out


def parse_html_to_matchups(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    table = find_matchups_table(soup)
    if not table:
        raise RuntimeError("Matchups table not found")
    return parse_matchups(table)


# -----------------------------
# Browser fetch (in-memory snapshot)
# -----------------------------

BASE = "https://www.dotabuff.com"


def fetch_counters_html_for_hero(driver, slug: str, timeout: int = 25) -> str:
    url = f"{BASE}/heroes/{slug}/counters"
    driver.get(url)
    time.sleep(0.4)
    wait_for_matchups_table(driver, timeout=timeout)
    # Light scrolling can help some lazy content appear
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.2)
    driver.execute_script("window.scrollTo(0, 0);")
    html = driver.execute_script("return document.documentElement.outerHTML;")
    return str(html)


# -----------------------------
# Main
# -----------------------------


def main():
    ap = argparse.ArgumentParser(
        description="Full extraction: discover slugs, fetch counters, parse, and save JSON.")
    ap.add_argument("--out-root", default="../content/matchups",
                    help="Output root directory (default: ../content/matchups)")
    ap.add_argument("--patch", default="auto",
                    help="Patch label (default: auto; resolves via dota2.com/patches)")
    ap.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True,
                    help="Run Chrome headless (default: True). Use --no-headless to disable.")
    ap.add_argument("--timeout", type=int, default=25,
                    help="Per-page load/wait timeout (seconds)")
    ap.add_argument("--sleep-min", type=float, default=2.5,
                    help="Min sleep between heroes")
    ap.add_argument("--sleep-max", type=float, default=4.5,
                    help="Max sleep between heroes")
    ap.add_argument("--only", nargs="*",
                    help="Optional subset of hero slugs to process")
    ap.add_argument("--force", action="store_true",
                    help="Force refresh all heroes, ignoring up-to-date checks")
    ap.add_argument("--retries", type=int, default=3,
                    help="Number of retries per hero on failure (default: 3)")
    ap.add_argument("--retry-sleep", type=float, default=5.0,
                    help="Seconds to sleep between retries (default: 5)")
    args = ap.parse_args()

    driver = build_driver(headless=args.headless)

    # Determine patch label (auto-detect from dota2.com when requested)
    def detect_latest_patch(driver, base_url: str = "https://www.dota2.com/patches/") -> Optional[str]:
        try:
            print(f"Detecting latest patch: opening {base_url} …")
            driver.get(base_url)
            time.sleep(0.8)  # allow redirect to settle
            current = driver.current_url or base_url
            print(f"Patch detection: redirected to {current}")
            parsed = urlparse(current)
            parts = [p for p in parsed.path.split("/") if p]
            patch_seg: Optional[str] = None
            for i, seg in enumerate(parts):
                if seg.lower() == "patches" and i + 1 < len(parts):
                    patch_seg = parts[i + 1]
                    break
            if not patch_seg and parts:
                patch_seg = parts[-1]
            if patch_seg:
                detected = patch_seg.strip().upper()
                print(
                    f"Patch detection: parsed patch segment '{patch_seg}' → '{detected}'")
                return detected
        except WebDriverException as e:
            print(
                f"Warning: failed to auto-detect patch from dota2.com: {e}", file=sys.stderr)
        return None

    if not args.patch or str(args.patch).lower() == "auto":
        print("Patch flag is 'auto'. Attempting to detect latest patch from dota2.com …")
        detected_patch = detect_latest_patch(driver)
        if detected_patch:
            patch_label = detected_patch
            print(f"Using detected patch: {patch_label}")
        else:
            patch_label = "7.XX"
            print(
                f"Falling back to default patch: {patch_label}", file=sys.stderr)
    else:
        patch_label = args.patch
        print(f"Using provided patch: {patch_label}")

    out_dir = Path(args.out_root).resolve() / patch_label
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {out_dir}")
    print(f"Patch: {patch_label}")

    saved_paths: List[Path] = []
    failures: List[str] = []
    skipped: List[str] = []

    try:
        print("Discovering hero slugs …")
        slugs = extract_hero_slugs(driver, timeout=args.timeout)
        if args.only:
            only = {s.lower() for s in args.only}
            slugs = [s for s in slugs if s in only]

        print(f"Discovered {len(slugs)} heroes.")

        for idx, slug in enumerate(slugs, start=1):
            print(f"[{idx}/{len(slugs)}] Processing hero: {slug}")

            # Skip if an up-to-date JSON already exists for this hero (unless --force)
            out_path = out_dir / f"{slug}.json"
            if not args.force and out_path.exists():
                try:
                    existing = json.loads(out_path.read_text(encoding="utf-8"))
                    # Prefer top-level updated_at; fall back to legacy metadata.updated_at
                    updated_at_str = (existing or {}).get("updated_at") or (
                        (existing or {}).get("metadata") or {}).get("updated_at")
                    if updated_at_str:
                        # Parse date from ISO string; treat 'Z' as UTC
                        try:
                            iso = updated_at_str.replace("Z", "+00:00")
                            dt_existing = dt.datetime.fromisoformat(iso)
                            existing_date = dt_existing.date()
                            today_utc = dt.datetime.utcnow().date()
                            if existing_date >= today_utc:
                                print(
                                    f"  - Up-to-date ({updated_at_str}). Skipping {slug}"
                                )
                                skipped.append(slug)
                                continue
                        except (ValueError, TypeError):
                            # If parsing fails, proceed to refresh
                            pass
                except (OSError, json.JSONDecodeError) as read_err:
                    print(
                        f"  - Warning: could not read existing JSON ({read_err}); will refresh",
                        file=sys.stderr,
                    )

            attempt = 0
            while attempt < args.retries:
                attempt += 1
                try:
                    print(
                        f"  - Attempt {attempt}/{args.retries}: fetching counters HTML…")
                    html = fetch_counters_html_for_hero(
                        driver, slug, timeout=args.timeout)

                    print("    Parsing matchups …")
                    matchups = parse_html_to_matchups(html)
                    # Ensure deterministic order: sort alphabetically by opponent slug
                    matchups = sorted(
                        matchups, key=lambda r: r.get("opponent", ""))

                    now_iso = (
                        dt.datetime.now(dt.timezone.utc)
                        .replace(microsecond=0)
                        .isoformat()
                        .replace("+00:00", "Z")
                    )
                    payload: Dict[str, Any] = {
                        "hero": slug,
                        "patch": patch_label,
                        "updated_at": now_iso,
                        "matchups": matchups,
                    }

                    out_path.write_text(
                        json.dumps(payload, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    saved_paths.append(out_path)
                    print(f"    Saved {out_path}")
                    break  # success for this hero
                except (TimeoutException, WebDriverException, RuntimeError, ValueError) as e:
                    print(f"    ERROR on hero '{slug}': {e}", file=sys.stderr)
                    if attempt < args.retries:
                        print(f"    Retrying in {args.retry_sleep:.1f}s …")
                        time.sleep(args.retry_sleep)
                    else:
                        failures.append(slug)
                        print("    Giving up after max retries.")

            # polite pacing between heroes
            time.sleep(random.uniform(args.sleep_min, args.sleep_max))

    finally:
        driver.quit()

    # Summary
    print("\n=== Summary ===")
    print(f"Saved:   {len(saved_paths)} files")
    print(f"Skipped: {len(skipped)} files (already up-to-date)")
    if failures:
        print(
            f"Failures ({len(failures)}): {', '.join(failures)}", file=sys.stderr)
    else:
        print("Failures: 0")

    # metadata.json
    metadata = {
        "updated_at": (
            dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "patch": patch_label,
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2,
                         ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {meta_path}")

    # Exit with error code if too many failures (more than 10% of heroes)
    total_heroes = len(slugs)
    if failures and len(failures) > total_heroes * 0.1:
        print(
            f"\nERROR: Too many failures ({len(failures)}/{total_heroes}). "
            "This may indicate rate limiting or anti-bot protection.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
