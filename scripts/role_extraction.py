# role_extractor.py
# Selenium scraper for hero roles from https://dota2protracker.com/hero/<hero>
# Requirements: selenium, beautifulsoup4, webdriver-manager (optional)
# Assumes a 'heroes' Python list of strings is available (percent-encoded with %20, lowercase).
# Example hero string: "shadow%20fiend"
#
# Output JSON per hero:
#   ../content/roles/7.39D/<hero-slug>.json
# where hero-slug = hero.replace("%20", "-")
#
# JSON format (UPDATED to include counts):
# {
#   "hero": "<hero-slug>",
#   "patch": "7.39D",
#   "updated_at": "YYYY-MM-DD",
#   "roles": ["support", "offlane", ...],        # roles with >5% of all matches
#   "counts": {                                   # NEW
#     "all roles": 12345,
#     "carry": 678,
#     "mid": 910,
#     "offlane": 1112,
#     "support": 1314,
#     "hard support": 1516
#   }
# }
from __future__ import annotations

import json
import os
import re
import sys
import time
import random
import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup  # type: ignore

from selenium import webdriver  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore

# If you prefer automatic driver management, uncomment these lines:
# from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
# from selenium.webdriver.chrome.service import Service  # type: ignore

# =============================================================================
# Configuration
# =============================================================================

PATCH = "7.39D"
ROLES_ORDERED = ["carry", "mid", "offlane", "support", "hard support"]
BASE_URL = "https://dota2protracker.com/hero/"
RETRIES_PER_HERO = 3
REQUEST_MIN_DELAY = 0.4
REQUEST_MAX_DELAY = 1.2
TIMEOUT_SECS = 10
THRESHOLD_PERCENT = 0.085  # 8.5%

TODAY = datetime.date.today().isoformat()

# Output directory
OUTPUT_DIR = (Path(__file__).parent / ".." /
              "content" / "roles" / PATCH).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Heroes list
# -----------------------------------------------------------------------------
heroes = [
    "abaddon",
    "chen",
    "dark%20seer",
    "shadow%20demon",
    "undying",
    "elder%20titan",
    "outworld%20destroyer",
    "anti-mage",
    "lycan",
    "enchantress",
    "doom",
    "ancient%20apparition",
    "lone%20druid",
    "pugna",
    "omniknight",
    "rubick",
    "io",
    "meepo",
    "keeper%20of%20the%20light",
    "razor",
    "tusk",
    "pangolier",
    "bristleback",
    "naga%20siren",
    "earthshaker",
    "tiny",
    "primal%20beast",
    "necrophos",
    "tinker",
    "oracle",
    "hoodwink",
    "sven",
    "slark",
    "brewmaster",
    "monkey%20king",
    "viper",
    "clockwerk",
    "weaver",
    "death%20prophet",
    "grimstroke",
    "kunkka",
    "underlord",
    "alchemist",
    "marci",
    "broodmother",
    "timbersaw",
    "medusa",
    "lina",
    "nature's%20prophet",
    "mars",
    "lion",
    "terrorblade",
    "winter%20wyvern",
    "muerta",
    "drow%20ranger",
    "dark%20willow",
    "sniper",
    "techies",
    "crystal%20maiden",
    "lich",
    "dawnbreaker",
    "shadow%20fiend",
    "centaur%20warrunner",
    "phantom%20assassin",
    "snapfire",
    "beastmaster",
    "nyx%20assassin",
    "magnus",
    "windranger",
    "invoker",
    "zeus",
    "lifestealer",
    "morphling",
    "bloodseeker",
    "tidehunter",
    "gyrocopter",
    "visage",
    "disruptor",
    "dragon%20knight",
    "riki",
    "phantom%20lancer",
    "spirit%20breaker",
    "chaos%20knight",
    "faceless%20void",
    "warlock",
    "witch%20doctor",
    "slardar",
    "ringmaster",
    "treant%20protector",
    "venomancer",
    "ursa",
    "templar%20assassin",
    "pudge",
    "arc%20warden",
    "juggernaut",
    "storm%20spirit",
    "clinkz",
    "skywrath%20mage",
    "leshrac",
    "enigma",
    "shadow%20shaman",
    "void%20spirit",
    "night%20stalker",
    "troll%20warlord",
    "phoenix",
    "jakiro",
    "ember%20spirit",
    "queen%20of%20pain",
    "sand%20king",
    "dazzle",
    "vengeful%20spirit",
    "huskar",
    "ogre%20magi",
    "puck",
    "mirana",
    "bane",
    "kez",
    "luna",
    "legion%20commander",
    "bounty%20hunter",
    "wraith%20king",
    "earth%20spirit",
    "batrider",
    "spectre",
    "silencer",
    "axe",
]

# =============================================================================
# Helpers
# =============================================================================


def hero_to_slug(hero: str) -> str:
    """Convert a percent-encoded hero name (e.g., 'shadow%20fiend') to slug 'shadow-fiend'."""
    return hero.lower().replace("%20", "-")


def to_int(s: str) -> Optional[int]:
    """Convert a numeric string like '12,345' to int, else None."""
    s = s.strip()
    m = re.search(r"([0-9][0-9,\.]*)", s)
    if not m:
        return None
    val = m.group(1).replace(",", "")
    try:
        return int(float(val))
    except Exception:
        return None


def _extract_support_count_simple(soup: "BeautifulSoup") -> Optional[int]:
    """
    Very targeted: parse the Support tile's yellow count.
    Structure observed:
      <img alt="Support"> 
      <div ...>
        <div class="yellow-new ...">8</div>
        <div class="green ...">50%</div>
      </div>
    CSS path: img[alt="Support"] + div .yellow-new
    """
    # 1) exact case (as in your snippet)
    node = soup.select_one('img[alt="Support"] + div .yellow-new')
    if node and (txt := node.get_text(strip=True)):
        m = re.search(r"([0-9][0-9,]*)", txt)
        if m:
            return int(m.group(1).replace(",", ""))

    # 2) case-insensitive fallback (in case alt is 'support')
    #    (BeautifulSoup CSS doesn't support i-flag; do a manual scan)
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip().lower()
        if alt == "support":
            # Adjacent sibling that contains the numbers
            sib = img.find_next_sibling()
            if sib:
                yellow = sib.select_one(".yellow-new")
                if yellow and (txt := yellow.get_text(strip=True)):
                    m = re.search(r"([0-9][0-9,]*)", txt)
                    if m:
                        return int(m.group(1).replace(",", ""))
    return None


def parse_counts_from_html(html: str) -> Dict[str, int]:
    """
    Parse total matches for 'All roles' and each role’s matches from page HTML.
    Returns a dict like:
      {
        "all roles": 12345,
        "carry": 678,
        "mid": 910,
        "offlane": 1112,
        "support": 1314,
        "hard support": 1516,
      }
    Uses multiple heuristics (regex + text scrapes) to be resilient to HTML changes.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()

    def find_count_for(label: str) -> Optional[int]:
        # Flexible pattern: "<label> ... 12,345 match(es)"
        pattern = re.compile(
            rf"{re.escape(label)}\b.*?([0-9][0-9,\.]*)\s*(?:match|matches)\b",
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(text)
        if m:
            return to_int(m.group(1))
        return None

    counts: Dict[str, int] = {}

    # All roles
    total = find_count_for("all roles")
    if total is None:
        # Secondary heuristic: first number near "All roles"
        near_pattern = re.compile(
            r"all roles(?:[^0-9]+)([0-9][0-9,\.]*)", re.I)
        m = near_pattern.search(text)
        if m:
            total = to_int(m.group(1))
    if total is not None:
        counts["all roles"] = total

    # Individual roles
    for role in ROLES_ORDERED:
        role_count = find_count_for(role)
        if role_count is None:
            alt = re.compile(
                rf"{re.escape(role)}(?:[^0-9]+)([0-9][0-9,\.]*)", re.I)
            m = alt.search(text)
            if m:
                role_count = to_int(m.group(1))
        if role_count is not None:
            counts[role] = role_count

    support_simple = _extract_support_count_simple(soup)
    if support_simple is not None:
        counts["support"] = support_simple

    return counts


def compute_selected_roles(counts: Dict[str, int]) -> List[str]:
    """Return roles whose matches are >5% of all matches."""
    total = counts.get("all roles")
    if not total or total <= 0:
        return []
    threshold = total * THRESHOLD_PERCENT
    selected = []
    for role in ROLES_ORDERED:
        c = counts.get(role, 0)
        if c > threshold:
            selected.append(role)
    return selected


def already_up_to_date(path: Path) -> bool:
    """Return True if JSON exists and its 'updated_at' equals TODAY."""
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("updated_at") == TODAY
    except Exception:
        return False


def save_role_json(path: Path, hero_slug: str, roles: List[str], counts: Dict[str, int]) -> None:
    """Write JSON including roles and counts (total + per-role)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "hero": hero_slug,
        "patch": PATCH,
        "updated_at": TODAY,
        "roles": roles,
        "counts": {
            # Ensure all keys exist even if some couldn't be parsed
            "all roles": counts.get("all roles", 0),
            "carry": counts.get("carry", 0),
            "mid": counts.get("mid", 0),
            "offlane": counts.get("offlane", 0),
            "support": counts.get("support", 0),
            "hard support": counts.get("hard support", 0),
        },
    }
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# =============================================================================
# Selenium setup
# =============================================================================

def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,2000")

    # If using webdriver-manager:
    # service = Service(ChromeDriverManager().install())
    # return webdriver.Chrome(service=service, options=opts)

    driver = webdriver.Chrome(options=opts)
    # Ensure all timeouts honor TIMEOUT_SECS (Selenium defaults to 120s for command executor)
    try:
        driver.set_page_load_timeout(TIMEOUT_SECS)
    except Exception:
        pass
    try:
        driver.set_script_timeout(TIMEOUT_SECS)
    except Exception:
        pass
    try:
        # Reduce default HTTP read timeout from 120s to TIMEOUT_SECS for all commands
        driver.command_executor.set_timeout(TIMEOUT_SECS)
    except Exception:
        pass
    return driver


def fetch_hero_html(driver: webdriver.Chrome, hero: str) -> str:
    """Load hero page and return HTML. Wait for 'All roles' to appear."""
    url = f"{BASE_URL}{hero}"
    driver.get(url)
    try:
        WebDriverWait(driver, TIMEOUT_SECS).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'all roles')]",
                )
            )
        )
    except Exception:
        time.sleep(2)  # best-effort fallback
    return driver.page_source


# =============================================================================
# Main loop
# =============================================================================

def process_hero(driver: webdriver.Chrome, hero: str) -> bool:
    """Process a single hero with retries and file skipping logic.

    Returns True if a network attempt was made (i.e., not skipped), else False.
    """
    hero_slug = hero_to_slug(hero)
    out_path = OUTPUT_DIR / f"{hero_slug}.json"

    if already_up_to_date(out_path):
        print(f"[skip] {hero_slug} already up-to-date ({out_path})")
        return False

    attempt = 0
    while attempt < RETRIES_PER_HERO:
        attempt += 1
        try:
            html = fetch_hero_html(driver, hero)
            counts = parse_counts_from_html(html)

            total = counts.get("all roles")
            if not total or total <= 0:
                raise RuntimeError(
                    "Failed to extract 'All roles' total matches")

            roles = compute_selected_roles(counts)
            save_role_json(out_path, hero_slug, roles, counts)
            print(
                f"[ok] {hero_slug}: total={total}, roles={roles}, counts={counts}")
            return True
        except Exception as e:
            print(
                f"[warn] {hero_slug} attempt {attempt}/{RETRIES_PER_HERO} failed: {e}")
            time.sleep(1.0 + attempt * 0.5)

    print(
        f"[fail] {hero_slug}: permanent failure after {RETRIES_PER_HERO} attempts")
    return True


def main() -> None:
    print(f"Saving roles to: {OUTPUT_DIR}")
    driver = build_driver()
    try:
        for hero in heroes:
            attempted = process_hero(driver, hero)
            if attempted:
                time.sleep(random.uniform(
                    REQUEST_MIN_DELAY, REQUEST_MAX_DELAY))
    finally:
        driver.quit()


if __name__ == "__main__":
    # Optional CLI override: python role_extractor.py "abaddon,shadow%20fiend"
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg:
            override = [h.strip().lower() for h in arg.split(",") if h.strip()]
            if override:
                heroes = override
    main()
