# -*- coding: utf-8 -*-
"""Run the whole validation pipeline in order.

Steps
-----
1. ``parse_logs.py``         archived games -> ``outcomes.csv``
2. ``anchor_validation.py``  LOO stability and per-anchor spread -> ``anchor_settings.csv``
3. ``reversi_tournament.py`` the two LLM-vs-LLM tournament tables

Usage
-----
    python run_all.py --logs ../log_game_records --tournament ../log_game_tournament_records/Reversi
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(script: str, *args: str) -> None:
    print("\n$ %s %s" % (script, " ".join(args)), flush=True)
    subprocess.run([PY, os.path.join(HERE, script), *args], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", required=True, help="root of log_game_records")
    ap.add_argument("--tournament", required=True,
                    help="directory holding the Reversi LLM-vs-LLM logs")
    args = ap.parse_args()

    run("parse_logs.py", "--logs", os.path.abspath(args.logs),
        "-o", os.path.join(HERE, "outcomes.csv"))
    run("anchor_validation.py")
    run("reversi_tournament.py", "--logs", os.path.abspath(args.tournament))

    print("\nDone. Artefacts written to %s" % HERE)


if __name__ == "__main__":
    main()
