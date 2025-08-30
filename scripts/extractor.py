#!/usr/bin/env python3
"""
Snapshot all Dotabuff hero counters pages.

Behavior:
- Saves to: ./snapshot/<YYYY-MM-DD>/<slug>.html
- Skips heroes whose snapshot file already exists (use --force to overwrite)
- Fails open: logs errors and continues

Usage:
  python snapshot_all_heroes.py --headless
  python snapshot_all_heroes.py --only pudge axe anti-mage
  python snapshot_all_heroes.py --force   # overwrite existing files
"""

import argparse
import datetime as dt
import os
import random
import sys
import time
from typing import List, Set

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "https://www.dotabuff.com"
HEROES_INDEX = f"{BASE}/heroes"


def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    )
    service = Service()  # assumes chromedriver is on PATH
    return webdriver.Chrome(service=service, options=opts)


def wait_for_matchups_table(driver: webdriver.Chrome, timeout: int = 25) -> None:
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "table.sortable, table")))

    def has_rows(drv):
        return drv.execute_script(
            """
            const tables = document.querySelectorAll('table.sortable, table');
            for (const t of tables) {
              const headText = (t.tHead?.innerText || '').toLowerCase();
              if (headText.includes('win rate') || headText.includes('matches')) {
                const rows = t.querySelectorAll('tbody tr, tr');
                if (rows.length >= 10) return true;
              }
            }
            return false;
            """
        )

    wait.until(has_rows)
    time.sleep(0.5)


def save_snapshot(driver: webdriver.Chrome, out_path: str) -> None:
    html = driver.execute_script("return document.documentElement.outerHTML;")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def extract_hero_slugs(driver: webdriver.Chrome, timeout: int = 20) -> List[str]:
    driver.get(HEROES_INDEX)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "a[href^='/heroes/']"))
    )
    time.sleep(0.3)
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href^='/heroes/']")
    slugs: Set[str] = set()

    for a in anchors:
        href = a.get_attribute("href") or ""
        if not href.startswith(f"{BASE}/heroes/"):
            continue
        tail = href[len(f"{BASE}/heroes/"):]
        parts = [p for p in tail.split("/") if p]
        if not parts:
            continue
        slug = parts[0].strip().lower()
        if slug in {
            "meta", "trends", "lanes", "played", "winning", "damage", "economy", "clips",
            "players", "guides", "items", "abilities", "builds", "overview",
        }:
            continue
        if any(c in slug for c in "?#&="):
            continue
        slugs.add(slug)

    return sorted(slugs)


def snapshot_counters_for_hero(
    driver: webdriver.Chrome, slug: str, out_root: str, date_str: str, timeout: int = 10
) -> str:
    url = f"{BASE}/heroes/{slug}/counters"
    driver.get(url)
    time.sleep(0.4)
    wait_for_matchups_table(driver, timeout=timeout)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.2)
    driver.execute_script("window.scrollTo(0, 0);")
    out_path = os.path.join(out_root, date_str, f"{slug}.html")
    save_snapshot(driver, out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="Snapshot ALL Dotabuff hero counters pages.")
    ap.add_argument("--out-root", default="../content/snapshot",
                    help="Root dir (default: ../content/snapshot)")
    ap.add_argument("--date", default=dt.date.today().strftime("%Y-%m-%d"),
                    help="Date string YYYY-MM-DD")
    ap.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True,
                    help="Run Chrome headless (default: True). Use --no-headless to disable.")
    ap.add_argument("--sleep-min", type=float, default=0.8,
                    help="Min sleep between heroes")
    ap.add_argument("--sleep-max", type=float, default=1.6,
                    help="Max sleep between heroes")
    ap.add_argument("--timeout", type=int, default=25,
                    help="Per-page load/wait timeout (seconds)")
    ap.add_argument("--only", nargs="*",
                    help="Optional subset of hero slugs to snapshot")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing files instead of skipping")
    args = ap.parse_args()

    driver = build_driver(headless=args.headless)

    failures, saved, skipped = [], [], []

    try:
        slugs = extract_hero_slugs(driver, timeout=args.timeout)
        if args.only:
            only = set(s.lower() for s in args.only)
            slugs = [s for s in slugs if s in only]

        print(f"Discovered {len(slugs)} hero slugs.")

        # Ensure date folder exists
        date_dir = os.path.join(args.out_root, args.date)
        os.makedirs(date_dir, exist_ok=True)

        for i, slug in enumerate(slugs, 1):
            out_path = os.path.join(date_dir, f"{slug}.html")

            # Skip if exists and not forcing
            if not args.force and os.path.exists(out_path):
                skipped.append(out_path)
                print(f"[{i}/{len(slugs)}] SKIP existing {slug} -> {out_path}")
                continue

            try:
                path = snapshot_counters_for_hero(
                    driver, slug, args.out_root, args.date, timeout=args.timeout
                )
                saved.append(path)
                print(f"[{i}/{len(slugs)}] Saved {slug} -> {path}")
            except Exception as e:
                failures.append(slug)
                print(f"[{i}/{len(slugs)}] ERROR for {slug}: {e}",
                      file=sys.stderr)

            time.sleep(random.uniform(args.sleep_min, args.sleep_max))
    finally:
        driver.quit()

    print("\n=== Summary ===")
    print(f"Saved:   {len(saved)} files")
    print(f"Skipped: {len(skipped)} files (existing)")
    if failures:
        print(
            f"Failures ({len(failures)}): {', '.join(failures)}", file=sys.stderr)


if __name__ == "__main__":
    main()
