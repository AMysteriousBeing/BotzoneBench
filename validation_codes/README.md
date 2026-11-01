# Validation code

Reproduces the two log-based analyses reported in the paper's
anchor-robustness subsection (§V-A) and the Reversi predictive-validity
sanity check (§V-B). Standard library only (Python 3.9+); no model calls and no
new games — everything is computed from the archived logs.

## Files

| File | Role |
|---|---|
| `anchors.csv` | Anchor roster: game, level, `anchor_order`, Botzone bot ID. |
| `parse_logs.py` | Turns `log_game_records/**` into `outcomes.csv`, one row per finished game. |
| `anchor_validation.py` | Leave-one-anchor-out stability and per-anchor spread; writes `anchor_settings.csv`. |
| `reversi_tournament.py` | Rebuilds the two LLM-vs-LLM tournament tables from the 40 Reversi games. |
| `run_all.py` | Runs all of the above in order. |

Generated artefacts: `outcomes.csv`, `anchor_settings.csv`.

## Quick start

```bash
python run_all.py --logs ../log_game_records \
                  --tournament ../log_game_tournament_records/Reversi
```

Expected output of the robustness step, which is what §V-A quotes:

```
settings            : 39
stable pass/fail    : 36/39
median spread       : 37.5 pp
median LOO delta    : 6.2 pp
max LOO delta       : 22.9 pp
```

`anchor_settings.csv` lists all 39 settings with their anchors, log range, full
win rate, per-anchor rates, spread, LOO rates and stability, so any single
number above can be traced back to the settings that produce it.

## Log layout and outcome mapping

```
log_game_records/<Game>/lv<N>/<model>/<index>-<side>[-re].log
```

* `<side>` — `llm` means the evaluated model holds seat 0 and the anchor bot
  seat 1; `bl` means the reverse. Every matchup is played twice with the seats
  swapped.
* `<index>` — position of the game inside the group, written in schedule order,
  so consecutive index blocks are consecutive anchors.
* `-re` — rematch of an id whose first attempt did not finish; skipped.

A log is a JSON array of move records; the last dictionary is the terminal
record and carries `winner`, the seat index of the winning player. A drawn game
either reports a non-seat value (2) or no `winner` at all. The multi-player
games store scores in the terminal record instead of a seat index; they are
mapped to an outcome as described in Sec. IV-B and do not enter the analyses
below.

## Rating rule behind the decision column

At level *k* the model plays that level's anchors. With `p = W / (W + L)`
(draws excluded) it advances to level *k+1* when `p >= 0.50`; otherwise the
rating is `(k, 2p)`. The robustness analysis reruns this pass/fail decision
after dropping one anchor, which is what "stable" refers to.

## Anchor robustness (§V-A)

A *setting* is one `(game, level, model)` group that

1. is evaluated against exactly four public anchors,
2. holds the scheduled 32 games — four matchups with swapped seats per anchor,
3. has contiguous log indices `0..31`, so the schedule order is intact,
4. has a decided result in every game.

Blocks of eight indices map to anchors in schedule order: `0-7 -> anchor 1`,
`8-15 -> anchor 2`, `16-23 -> anchor 3`, `24-31 -> anchor 4`. This is the
logging order of the evaluation pipeline, reconstructed from
`bot_info_reference.py` and the log index rather than from an anchor ID inside
the log.

Two statistics are computed per setting:

* **per-anchor win rate** — the win rate inside each anchor's block; the
  **spread** is `max - min` in percentage points;
* **leave-one-anchor-out** — the win rate recomputed after dropping each anchor
  in turn; the setting is **stable** when every LOO rate stays on the same side
  of the 50% threshold as the full-set rate, and the **LOO delta** is the
  largest absolute change from the full-set rate.

## Reversi direct play (§V-B)

```
log_game_tournament_records/Reversi/{A}_{B}_{i}[-re].log
```

The harness always builds `bots = [llm1, llm2]`, so in a file named
`{A}_{B}_{i}` model A holds seat 0 and model B seat 1, for both `i = 0` and
`i = 1`. Reversi is deterministic and every log opens with a move by
`player: 0`, so seat 0 is the first mover: each pair plays two games with A
moving first and two with B moving first. That is the "wins as first mover /
as second mover (two games each)" layout of the head-to-head table; normalising
each file to `(first mover, second mover, index)` gives 20 ordered pairs × 2
games = 40.
