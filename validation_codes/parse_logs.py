# -*- coding: utf-8 -*-
"""Parse archived Botzone game logs into a flat outcome table.

Log layout produced by the evaluation harness::

    log_game_records/<Game>/lv<N>/<model>/<index>-<side>[-re].log

``<side>``
    ``llm``  -> the evaluated model holds seat 0 and the anchor bot seat 1.
    ``bl``   -> the anchor bot holds seat 0 and the evaluated model seat 1.
    Every matchup is played twice with the seats swapped.

``<index>``
    Position of the game inside the ``(game, level, model)`` group. Logs are
    written in schedule order, so a group of 32 games is four consecutive
    blocks of eight, one per anchor (see ``README.md``).

``-re``
    Rematch of an id whose first attempt did not finish. Skipped here: the
    robustness analysis uses finished games only.

A log is a JSON array of move records. The last dictionary in the array is the
terminal record and carries ``winner``, the seat index of the winning player:

===================  ==============================================
``winner`` = 0 or 1  ``win`` / ``loss`` for the evaluated model
``winner`` = 2       ``draw`` (a few games report a drawn game this way)
no ``winner`` key    ``draw`` for the five two-player games, whose drawn
                     games carry no winner; ``n/a`` for the multi-player
                     games, which store scores in the terminal record and are
                     mapped to an outcome as described in the paper (Sec. IV-B)
===================  ==============================================

Output columns
--------------
``game, level, model, index, side, outcome``

Usage
-----
    python parse_logs.py --logs ../../log_game_records -o outcomes.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter

LOG_RE = re.compile(r"^(?P<index>\d+)-(?P<side>llm|bl)(?P<retry>-re)?\.log$")
LEVEL_RE = re.compile(r"^lv(?P<level>\d+)$")

# Multi-player games: the terminal record carries scores, not a seat index.
SCORE_BASED = {"FightTheLandlord", "ChineseStandardMahjong", "TexasHoldem2p"}


def read_terminal(path: str) -> dict | None:
    """Return the terminal record of a log, or ``None`` if it is unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            seq = json.load(fh)
    except (ValueError, OSError):
        return None
    if not isinstance(seq, list) or not seq:
        return None
    for item in reversed(seq):
        if isinstance(item, dict):
            return item
    return None


def judge(terminal: dict, llm_seat: int, game: str) -> str:
    """Outcome from the evaluated model's point of view."""
    if "winner" not in terminal:
        return "n/a" if game in SCORE_BASED else "draw"
    winner = terminal["winner"]
    if winner not in (0, 1):
        return "draw"
    return "win" if winner == llm_seat else "loss"


def iter_logs(root: str):
    for game in sorted(os.listdir(root)):
        game_dir = os.path.join(root, game)
        if not os.path.isdir(game_dir):
            continue
        for level_dir in sorted(os.listdir(game_dir)):
            level_match = LEVEL_RE.match(level_dir)
            if not level_match:
                continue
            level_path = os.path.join(game_dir, level_dir)
            if not os.path.isdir(level_path):
                continue
            for model in sorted(os.listdir(level_path)):
                model_path = os.path.join(level_path, model)
                if not os.path.isdir(model_path):
                    continue
                for name in sorted(os.listdir(model_path)):
                    match = LOG_RE.match(name)
                    if not match or match.group("retry"):
                        continue
                    yield (
                        game,
                        "Lv%d" % int(level_match.group("level")),
                        model,
                        int(match.group("index")),
                        match.group("side"),
                        os.path.join(model_path, name),
                    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", required=True,
                    help="root of log_game_records, e.g. ../log_game_records")
    ap.add_argument("-o", "--out", default="outcomes.csv")
    args = ap.parse_args()

    rows = []
    for game, level, model, index, side, path in iter_logs(args.logs):
        terminal = read_terminal(path)
        outcome = "n/a" if terminal is None else judge(
            terminal, 0 if side == "llm" else 1, game)
        rows.append({
            "game": game,
            "level": level,
            "model": model,
            "index": index,
            "side": side,
            "outcome": outcome,
        })

    fieldnames = ["game", "level", "model", "index", "side", "outcome"]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("games parsed: %d  %s" % (len(rows), dict(Counter(r["outcome"] for r in rows))))
    print("written     : %s" % args.out)


if __name__ == "__main__":
    main()
