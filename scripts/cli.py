#!/usr/bin/env python3
"""
Dota counter CLI:
- Choose a date (autocomplete from ../content/counter/*).
- Enter up to five enemy hero slugs (autocomplete from ../content/counter/<date>/*.json; type END to stop early).
- Assign a weight (0..1, default 1) per enemy.
- Output the top 10 heroes with highest combined counter score (weighted log-odds of winrates).

Assumes JSON files shaped like:
{
  "hero": "<slug>",
  "date": "YYYY-MM-DD",
  "matchups": [
    {"opponent": "<slug>", "winrate": 56.31, "disadvantage": -3.11, "matches": 153542},
    ...
  ]
}
"""

import json
import math
import os
import readline
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path("../content/counter")

# ---------- Utilities ----------


def list_dates() -> List[str]:
    if not BASE_DIR.exists():
        return []
    return sorted([p.name for p in BASE_DIR.iterdir() if p.is_dir()])


def list_hero_slugs_for_date(date: str) -> List[str]:
    date_dir = BASE_DIR / date
    slugs = []
    for p in sorted(date_dir.glob("*.json")):
        slugs.append(p.stem.lower())
    return slugs


def load_date_data(date: str) -> Dict[str, Dict[str, float]]:
    """
    Returns:
      data[candidate_hero][opponent_hero] = winrate (0..100 float)
    """
    date_dir = BASE_DIR / date
    data: Dict[str, Dict[str, float]] = {}
    for fp in date_dir.glob("*.json"):
        with open(fp, "r", encoding="utf-8") as f:
            obj = json.load(f)
        hero = str(obj.get("hero", fp.stem)).lower()
        matchups = obj.get("matchups", [])
        opp_map: Dict[str, float] = {}
        for m in matchups:
            opp = str(m.get("opponent", "")).lower()
            wr = m.get("winrate", None)
            if isinstance(wr, (int, float)):
                opp_map[opp] = float(wr)
        if opp_map:
            data[hero] = opp_map
    return data


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def pct_to_logodds(pct: float) -> float:
    """Convert 0..100% -> log-odds, with clamping to avoid infinities."""
    p = clamp(pct / 100.0, 0.005, 0.995)  # 0.5%..99.5%
    return math.log(p / (1.0 - p))


def logodds_to_pct(lo: float) -> float:
    """Convert log-odds -> 0..100%."""
    p = 1.0 / (1.0 + math.exp(-lo))
    return 100.0 * p

# ---------- Readline completion ----------


class ListCompleter:
    def __init__(self, options: List[str]):
        self.set_options(options)

    def set_options(self, options: List[str]):
        self.options = sorted(set(options))
        self.matches: List[str] = []

    def complete(self, text, state):
        if state == 0:
            if not text:
                self.matches = self.options[:]
            else:
                t = text.lower()
                self.matches = [
                    s for s in self.options if s.lower().startswith(t)]
        try:
            return self.matches[state]
        except IndexError:
            return None


def prompt_with_completion(prompt_text: str, completer: ListCompleter, default: Optional[str] = None) -> str:
    old = readline.get_completer()
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
    try:
        s = input(
            f"{prompt_text}{f' [{default}]' if default else ''}: ").strip()
        if not s and default is not None:
            s = default
        return s
    finally:
        readline.set_completer(old)

# ---------- CLI steps ----------


def choose_date() -> str:
    dates = list_dates()
    if not dates:
        sys.exit("No date folders found in ./counter/. Make sure your data exists.")
    comp = ListCompleter(dates)
    while True:
        date = prompt_with_completion(
            "Select date (Tab to autocomplete)", comp, default=dates[-1])
        if date in dates:
            return date
        print(f"Unknown date: {date}. Available: {', '.join(dates)}")


def collect_enemies(date: str, max_enemies: int = 5) -> List[Tuple[str, float]]:
    slugs = list_hero_slugs_for_date(date)
    comp = ListCompleter(slugs + ["END"])
    picked: List[Tuple[str, float]] = []

    print("\nEnter up to five enemy hero slugs (type END to finish).")
    while len(picked) < max_enemies:
        default = None
        enemy = prompt_with_completion(
            f"Enemy {len(picked)+1}", comp, default=default).lower()
        if enemy == "end":
            break
        if enemy not in slugs:
            print(
                f"'{enemy}' is not a known hero slug for {date}. Try again (Tab to browse).")
            continue
        # Weight prompt
        while True:
            w_raw = input("  Weight 0..1 (default 1): ").strip()
            if not w_raw:
                w = 1.0
                break
            try:
                w = float(w_raw)
                if 0.0 <= w <= 1.0:
                    break
            except ValueError:
                pass
            print("  Invalid weight. Enter a number between 0 and 1.")
        picked.append((enemy, w))
    if not picked:
        sys.exit("No enemies provided. Exiting.")
    return picked

# ---------- Scoring ----------


def score_candidates(
    data: Dict[str, Dict[str, float]],
    enemies: List[Tuple[str, float]],
) -> List[Dict]:
    """
    For each candidate hero H:
      score = logistic( (sum_i w_i * logit(winrate(H vs enemy_i))) / (sum_i w_i over enemies with data) )

    - Ignores enemies for which the candidate has no matchup data.
    - Excludes candidate heroes that the user listed as enemies.
    """
    enemy_set = {e for e, _ in enemies}
    results = []
    for hero, opp_map in data.items():
        if hero in enemy_set:
            continue

        weighted_sum = 0.0
        weight_total = 0.0
        per_enemy = []
        for enemy, w in enemies:
            wr = opp_map.get(enemy)
            if wr is None:
                per_enemy.append({"enemy": enemy, "winrate": None})
                continue
            lo = pct_to_logodds(wr)
            weighted_sum += w * lo
            weight_total += w
            per_enemy.append({"enemy": enemy, "winrate": wr})

        if weight_total <= 0.0:
            # No usable data for this hero vs selected enemies
            continue

        combined_pct = logodds_to_pct(weighted_sum / weight_total)
        results.append(
            {
                "hero": hero,
                "combined": combined_pct,
                "per_enemy": per_enemy,
            }
        )

    # Rank by combined score desc
    results.sort(key=lambda x: x["combined"], reverse=True)
    return results

# ---------- Pretty printing ----------


def print_top(results: List[Dict], enemies: List[Tuple[str, float]], top_k: int = 10):
    print("\n=== Recommendations (Top {0}) ===".format(
        min(top_k, len(results))))
    enemy_headers = [f"{e} (w={w:g})" for e, w in enemies]
    # Header
    print("{:24} {:>8}  {}".format("Hero", "Combined",
          " | ".join(f"{h:>18}" for h in enemy_headers)))
    print("-" * (26 + 10 + 3 + len(enemy_headers) * 21))

    for r in results[:top_k]:
        hero = r["hero"]
        combined = f"{r['combined']:.2f}%"
        per_enemy_map = {pe["enemy"]: pe["winrate"] for pe in r["per_enemy"]}
        cols = []
        for e, _ in enemies:
            wr = per_enemy_map.get(e)
            cols.append(f"{(f'{wr:.2f}%' if wr is not None else '—'):>18}")
        print("{:24} {:>8}  {}".format(hero, combined, " | ".join(cols)))

# ---------- Main ----------


def main():
    date = choose_date()
    enemies = collect_enemies(date)
    print(f"\nSelected date: {date}")
    print("Enemies:", ", ".join([f"{e}(w={w:g})" for e, w in enemies]))

    data = load_date_data(date)
    if not data:
        sys.exit(f"No JSON data found for {date} in {BASE_DIR}/{date}")

    results = score_candidates(data, enemies)
    if not results:
        sys.exit(
            "No candidates had usable matchup data against the selected enemies.")

    print_top(results, enemies, top_k=10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
