#!/usr/bin/env python3
"""Rebuild the two Reversi tournament tables from the 40 archived games.

Seat assignment
---------------
The harness always builds ``bots = [Bot(llm_bot1), Bot(llm_bot2)]``, so in a log
named ``{A}_{B}_{i}.log`` model A holds seat 0 and model B seat 1, for both
``i = 0`` and ``i = 1``. Reversi is deterministic and every log opens with a
move by ``player: 0``, so seat 0 is the first mover. Each pair therefore plays
two games with A moving first and two with B moving first -- the "wins as first
mover / as second mover (two games each)" layout of the head-to-head table.

A pair appears under both names, ``A_B_i`` and ``B_A_i``; normalising the id to
``(first mover, second mover, index)`` gives 20 ordered pairs x 2 games = 40.

Output
------
The head-to-head matrix and the per-model win totals, i.e. the two tournament
tables reported in the paper.

Usage
-----
    python reversi_tournament.py [--logs PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

MODELS = ["Gemini3Pro_Preview", "ClaudeSonnet4.5", "DeepSeek3.2",
          "Qwen3_235_Instruct", "GPT5.2"]
SHORT = {"Gemini3Pro_Preview": "Gemini3-Pro", "ClaudeSonnet4.5": "Claude-Sonnet-4.5",
         "DeepSeek3.2": "DeepSeek-3.2", "Qwen3_235_Instruct": "Qwen3-235B-Instr.",
         "GPT5.2": "GPT-5.2"}
ABBR = {"Gemini3-Pro": "Gemini", "Claude-Sonnet-4.5": "Claude",
        "Qwen3-235B-Instr.": "Qwen", "DeepSeek-3.2": "DeepSeek", "GPT-5.2": "GPT"}
ORDER = ["Gemini3-Pro", "Claude-Sonnet-4.5", "Qwen3-235B-Instr.",
         "DeepSeek-3.2", "GPT-5.2"]

NAME_RE = re.compile(r"^(%s)_(%s)_(\d+)(-re\d*)?\.log$"
                     % ("|".join(MODELS), "|".join(MODELS)))


def load(logs: str) -> dict[tuple[str, str, int], str]:
    """(first mover, second mover, index) -> winner."""
    games: dict[tuple[str, str, int], str] = {}
    for fn in sorted(os.listdir(logs)):
        match = NAME_RE.match(fn)
        if not match:
            continue
        first, second, idx = SHORT[match.group(1)], SHORT[match.group(2)], int(match.group(3))
        with open(os.path.join(logs, fn), encoding="utf-8", errors="replace") as fh:
            seq = json.load(fh)
        winner = None
        for record in reversed(seq):
            if isinstance(record, dict) and "winner" in record:
                winner = record["winner"]
                break
        if winner not in (0, 1):
            raise SystemExit("unexpected terminal record in %s" % fn)
        games[(first, second, idx)] = first if winner == 0 else second
    return games


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--logs", default=os.path.join(
        here, "..", "log_game_tournament_records", "Reversi"))
    args = ap.parse_args()

    games = load(args.logs)
    print("logs: %s  (%d games)" % (os.path.normpath(args.logs), len(games)))
    print()

    print("=== wins as first mover / as second mover ===")
    print("%-20s%s" % ("", "".join("%14s" % ABBR[c] for c in ORDER)))
    for row in ORDER:
        cells = []
        for col in ORDER:
            if row == col:
                cells.append("%14s" % "---")
                continue
            first = sum(1 for i in (0, 1) if games.get((row, col, i)) == row)
            second = sum(1 for i in (0, 1) if games.get((col, row, i)) == row)
            cells.append("%14s" % ("%d/%d" % (first, second)))
        print("%-20s%s" % (ABBR[row], "".join(cells)))
    print()

    print("=== tournament wins (out of 16) ===")
    totals = sorted(((sum(1 for v in games.values() if v == m), m) for m in ORDER),
                    reverse=True)
    for wins, model in totals:
        print("%-20s%3d" % (model, wins))
    print()

    expected = len(ORDER) * (len(ORDER) - 1) * 2
    if len(games) != expected:
        print("note: %d games found, %d expected for a double round-robin"
              % (len(games), expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
