# -*- coding: utf-8 -*-
"""Anchor robustness: leave-one-anchor-out stability and per-anchor spread.

Reproduces the two log-based analyses of the paper's anchor-robustness
subsection.

Leave-one-anchor-out (LOO)
    For a setting with ``k`` anchors the model's win rate is recomputed after
    removing one anchor in turn. A setting is *stable* when every LOO rate
    stays on the same side of the 50% threshold as the full-set rate, and the
    LOO delta is the largest absolute change from the full-set rate.

Per-anchor spread
    The win rate against each anchor separately; the spread is ``max - min``
    in percentage points and measures same-level heterogeneity.

A *setting* is one ``(game, level, model)`` group that is evaluated against
exactly four anchors, holds the scheduled 32 games (4 matchups x 2 seat orders
per anchor), has contiguous log indices ``0..31``, and has a decided result in
every game. Consecutive blocks of eight indices map to the anchors in schedule
order: ``0-7 -> anchor 1, 8-15 -> anchor 2, 16-23 -> anchor 3, 24-31 -> anchor 4``.

Outputs
-------
``anchor_settings.csv``  one row per setting: anchors, log range, full win
                         rate, pass/fail decision, per-anchor rates, spread,
                         LOO rates and stability.

Usage
-----
    python anchor_validation.py [--outcomes outcomes.csv] [--anchors anchors.csv]
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

GAMES_PER_ANCHOR = 8
N_ANCHORS = 4
PASS_THRESHOLD = 0.5


def load_anchors(path: str) -> dict[tuple[str, str], list[str]]:
    table: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[(row["game"], row["level"])].append(
                (int(row["anchor_order"]), row["bot_id"]))
    return {k: [bot_id for _, bot_id in sorted(v)] for k, v in table.items()}


def load_outcomes(path: str) -> dict[tuple[str, str, str], dict[int, str]]:
    groups: dict[tuple[str, str, str], dict[int, str]] = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["game"], row["level"], row["model"])
            groups[key][int(row["index"])] = row["outcome"]
    return groups


def qualifies(outcomes: dict[int, str], anchors: list[str] | None) -> bool:
    """True when the group is a regular four-anchor setting."""
    if not anchors or len(anchors) != N_ANCHORS:
        return False
    expected = N_ANCHORS * GAMES_PER_ANCHOR
    if len(outcomes) != expected or sorted(outcomes) != list(range(expected)):
        return False
    return all(o in ("win", "loss") for o in outcomes.values())


def analyse(outcomes: dict[int, str]) -> dict:
    k = N_ANCHORS
    per_anchor = len(outcomes) // k
    wins = sum(1 for o in outcomes.values() if o == "win")
    n = len(outcomes)
    full = wins / n

    block_wins = []
    for i in range(k):
        block = range(i * per_anchor, (i + 1) * per_anchor)
        block_wins.append(sum(1 for j in block if outcomes[j] == "win"))
    anchor_rates = [b / per_anchor for b in block_wins]

    loo = [(wins - b) / (n - per_anchor) for b in block_wins]
    return {
        "n_games": n,
        "wins": wins,
        "full_win_rate": full,
        "decision": "pass" if full >= PASS_THRESHOLD else "fail",
        "anchor_rates": anchor_rates,
        "spread_pp": (max(anchor_rates) - min(anchor_rates)) * 100.0,
        "loo_rates": loo,
        "loo_delta_pp": max(abs(r - full) for r in loo) * 100.0,
        "stable": all((r >= PASS_THRESHOLD) == (full >= PASS_THRESHOLD) for r in loo),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outcomes", default=os.path.join(HERE, "outcomes.csv"))
    ap.add_argument("--anchors", default=os.path.join(HERE, "anchors.csv"))
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "anchor_settings.csv"))
    args = ap.parse_args()

    anchors = load_anchors(args.anchors)
    groups = load_outcomes(args.outcomes)

    rows = []
    for (game, level, model), outcomes in sorted(groups.items()):
        anchor_ids = anchors.get((game, level))
        if not qualifies(outcomes, anchor_ids):
            continue
        stats = analyse(outcomes)
        rows.append({
            "game": game,
            "level": level,
            "model": model,
            "n_anchors": len(anchor_ids),
            "anchor_ids": ";".join(anchor_ids),
            "games_per_anchor": stats["n_games"] // len(anchor_ids),
            "log_index_range": "0-%d" % (stats["n_games"] - 1),
            "wins": stats["wins"],
            "full_win_rate": "%.4f" % stats["full_win_rate"],
            "decision": stats["decision"],
            "per_anchor_win_rates": ";".join("%.4f" % r for r in stats["anchor_rates"]),
            "spread_pp": "%.1f" % stats["spread_pp"],
            "loo_rates": ";".join("%.4f" % r for r in stats["loo_rates"]),
            "loo_delta_pp": "%.1f" % stats["loo_delta_pp"],
            "loo_stable": "yes" if stats["stable"] else "no",
        })

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    spreads = [float(r["spread_pp"]) for r in rows]
    deltas = [float(r["loo_delta_pp"]) for r in rows]
    stable = sum(1 for r in rows if r["loo_stable"] == "yes")

    print("settings            : %d" % len(rows))
    print("stable pass/fail    : %d/%d" % (stable, len(rows)))
    print("median spread       : %.1f pp" % statistics.median(spreads))
    print("median LOO delta    : %.1f pp" % statistics.median(deltas))
    print("max LOO delta       : %.1f pp" % max(deltas))
    print("written             : %s" % args.out)


if __name__ == "__main__":
    main()
