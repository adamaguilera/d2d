#!/usr/bin/env python3
"""
Download Dota 2 hero portraits from Valve's dota_react CDN, named by Dotabuff slugs.

- Discovers hero slugs on https://www.dotabuff.com/heroes
- Downloads from:
    https://cdn.steamstatic.com/apps/dota2/images/dota_react/heroes/<cdn_name>.png
  where <cdn_name> is usually the slug with '-' → '_' plus a few legacy exceptions.
- Saves to: ./images/heroes/<slug>.png (create dirs as needed)

Usage:
  python fetch_hero_pngs.py
  python fetch_hero_pngs.py --force
  python fetch_hero_pngs.py --out-root ./assets
  python fetch_hero_pngs.py --only pudge axe anti-mage

Requires:
  pip install selenium requests

Note:
  We use Selenium to grab Dotabuff slugs to avoid Cloudflare/anti-bot hiccups.
"""

import argparse
import os
import sys
import time
from typing import Dict, Iterable, List, Set

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DOTABUFF_HEROES = "https://www.dotabuff.com/heroes"
CDN_BASE = "https://cdn.steamstatic.com/apps/dota2/images/dota_react/heroes"

# Known CDN filename overrides/multiples for a given Dotabuff slug.
# We will try candidates in order until one works (HTTP 200).
CDN_ALIASES: Dict[str, List[str]] = {
    # Definite mismatches
    "underlord": ["abyssal_underlord"],
    "lifestealer": ["life_stealer"],
    "shadow-fiend": ["shadow_fiend", "nevermore"],
    # Historical/engine names that sometimes show up:
    "clockwerk": ["clockwerk", "rattletrap"],
    "windranger": ["windranger", "windrunner"],
    "outworld-destroyer": ["outworld_destroyer", "obsidian_destroyer", "outworld_devourer"],
    "io": ["io", "wisp"],
    "timbersaw": ["timbersaw", "shredder"],
    "natures-prophet": ["natures_prophet", "furion"],
    "wraith-king": ["wraith_king", "skeleton_king"],
    "treant-protector": ["treant_protector", "treant"],
    "magnus": ["magnus", "magnataur"],
    "queen-of-pain": ["queen_of_pain"],
    # Many heroes are straight hyphen→underscore; no alias needed.
}


def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    # A realistic UA helps with Cloudflare/CDN
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    service = Service()  # expects chromedriver on PATH
    return webdriver.Chrome(service=service, options=opts)


def get_dotabuff_slugs(driver: webdriver.Chrome, timeout: int = 25) -> List[str]:
    """Visit Dotabuff heroes index and extract hero slugs from /heroes/<slug> links."""
    driver.get(DOTABUFF_HEROES)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "a[href^='/heroes/']"))
    )
    time.sleep(0.3)

    slugs: Set[str] = set()
    for a in driver.find_elements(By.CSS_SELECTOR, "a[href^='/heroes/']"):
        href = a.get_attribute("href") or ""
        if not href.startswith("https://www.dotabuff.com/heroes/"):
            continue
        tail = href.split("/heroes/", 1)[-1]
        slug = tail.split("/", 1)[0].strip().lower()
        if not slug or any(c in slug for c in "?#&="):
            continue
        # Filter out non-hero pages under /heroes
        if slug in {
            "meta", "trends", "lanes", "played", "winning", "damage", "economy", "clips",
            "players", "guides", "items", "abilities", "builds", "overview",
        }:
            continue
        slugs.add(slug)
    return sorted(slugs)


def slug_to_cdn_candidates(slug: str) -> List[str]:
    """
    Produce ordered candidate CDN basenames for a slug (without .png).
    1) direct hyphen→underscore (most common)
    2) known aliases (if any)
    De-duplicate while preserving order.
    """
    candidates = [slug.replace("-", "_")]
    if slug in CDN_ALIASES:
        candidates.extend(CDN_ALIASES[slug])
    # de-dupe preserve order
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq


def download_png(session: requests.Session, cdn_base: str, cdn_name: str, out_path: str) -> bool:
    url = f"{cdn_base}/{cdn_name}.png"
    try:
        r = session.get(url, timeout=20)
        if r.status_code == 200 and r.content:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
        return False
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Fetch Dota2 hero PNGs by Dotabuff slugs into ./content/images/heroes/<slug>.png")
    ap.add_argument("--out-root", default="./content/images",
                    help="Root directory (default: ./content/images)")
    ap.add_argument("--headless", action=argparse.BooleanOptionalAction,
                    default=True, help="Run Chrome headless (default True)")
    ap.add_argument("--timeout", type=int, default=25,
                    help="Dotabuff load timeout (default 25s)")
    ap.add_argument("--only", nargs="*",
                    help="Optional subset of slugs to fetch")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing files")
    args = ap.parse_args()

    out_dir = os.path.join(args.out_root, "heroes")
    os.makedirs(out_dir, exist_ok=True)

    driver = build_driver(headless=args.headless)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    })

    saved, skipped, failed = 0, 0, 0
    try:
        slugs = get_dotabuff_slugs(driver, timeout=args.timeout)
        if args.only:
            want = set(s.lower() for s in args.only)
            slugs = [s for s in slugs if s in want]

        print(f"Found {len(slugs)} hero slugs on Dotabuff.")

        for i, slug in enumerate(slugs, 1):
            out_path = os.path.join(out_dir, f"{slug}.png")
            if os.path.exists(out_path) and not args.force:
                skipped += 1
                print(f"[{i}/{len(slugs)}] SKIP existing {slug}")
                continue

            ok = False
            for cdn_name in slug_to_cdn_candidates(slug):
                if download_png(session, CDN_BASE, cdn_name, out_path):
                    print(f"[{i}/{len(slugs)}] Saved {slug} <- {cdn_name}.png")
                    saved += 1
                    ok = True
                    break
            if not ok:
                failed += 1
                print(
                    f"[{i}/{len(slugs)}] FAIL  {slug} (no CDN match)", file=sys.stderr)
            time.sleep(0.05)  # be polite
    finally:
        driver.quit()

    print("\n=== Summary ===")
    print(f"Saved:   {saved}")
    print(f"Skipped: {skipped}")
    print(f"Failed:  {failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
