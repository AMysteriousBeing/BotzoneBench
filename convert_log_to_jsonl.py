"""
修复版的 convert_logs_to_jsonl.py

主要修复：
1. is_active_llm_record() 现在严格过滤 system_prompt 为 'NA' 或空值的记录
2. build_llm_records() 只保留 is_active_llm_record() 返回 True 的记录
3. 只有有效的 LLM 决策记录才会被写入 jsonl
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "processed_datasets"

SINGLE_LLM_ROOT = ROOT / "log_llm_records"
SINGLE_GAME_ROOT = ROOT / "log_game_records"
TOURNAMENT_LLM_ROOT = ROOT / "log_llm_tournament_records"
TOURNAMENT_GAME_ROOT = ROOT / "log_game_tournament_records"

ENTRY_RE = re.compile(
    r"^(?P<timestamp>\d{2}_\d{2}_\d{2}_\d{2}_\d{2})\t(?P<kind>Debug|Response):\s?(?P<payload>.*)$"
)
SINGLE_LLM_STEM_RE = re.compile(r"^(?P<round>.+?)-(?P<seat>\d+)(?P<rematch>-re)?$")
SINGLE_GAME_STEM_RE = re.compile(
    r"^(?P<round>.+?)-(?P<starter>llm|bl)(?P<rematch>-re)?$"
)
TOURNAMENT_LLM_STEM_RE = re.compile(r"^(?P<match_stem>.+)-(?P<seat>\d+)$")
TOURNAMENT_MATCH_RE = re.compile(r"^(?P<pair>.+)_(?P<round>\d+(?:-re\d*)?)$")

PASSIVE_RESPONSES = {"PASS", "NONE", "None", ""}
KNOWN_TOURNAMENT_LLM_NAMES = {
    "Qwen3_235_Thinking",
    "Qwen3_235_Instruct",
    "DeepSeek3.2",
    "Gemini3Pro_Preview",
    "ClaudeSonnet4.5",
    "GPT5.2",
    "GLM4.6",
    "KimiK2",
}

# 最短有效 system_prompt 长度（根据实际数据，约50字符是最短的"真实"system_prompt）
MIN_VALID_SYSTEM_PROMPT_LEN = 50


@dataclass
class ParsedLogRecord:
    timestamp: str | None
    debug_raw: str | None
    response_raw: str | None
    debug_value: Any
    response_value: Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Botzone benchmark logs into JSONL datasets (filtered)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated JSONL files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count records without writing files.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_loose_value(raw: str | None) -> Any:
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        return ast.literal_eval(text)
    except Exception:
        return text


def parse_llm_log(path: Path) -> list[ParsedLogRecord]:
    records: list[ParsedLogRecord] = []
    pending: dict[str, Any] | None = None

    def flush_pending() -> None:
        nonlocal pending
        if not pending:
            return
        records.append(
            ParsedLogRecord(
                timestamp=pending.get("timestamp"),
                debug_raw=pending.get("debug_raw"),
                response_raw=pending.get("response_raw"),
                debug_value=parse_loose_value(pending.get("debug_raw")),
                response_value=parse_loose_value(pending.get("response_raw")),
            )
        )
        pending = None

    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        if set(line.strip()) == {"-"}:
            flush_pending()
            continue
        match = ENTRY_RE.match(line)
        if not match:
            if pending is not None and pending.get("last_field"):
                field = pending["last_field"]
                pending[field] = f"{pending[field]}\n{line}" if pending[field] else line
            continue

        timestamp = match.group("timestamp")
        kind = match.group("kind").lower()
        payload = match.group("payload")
        field = f"{kind}_raw"

        if pending is None:
            pending = {
                "timestamp": timestamp,
                "debug_raw": None,
                "response_raw": None,
                "last_field": field,
            }
        elif pending["timestamp"] != timestamp or pending.get(field) is not None:
            flush_pending()
            pending = {
                "timestamp": timestamp,
                "debug_raw": None,
                "response_raw": None,
                "last_field": field,
            }

        pending[field] = payload
        pending["last_field"] = field

    flush_pending()
    return records


def normalize_debug_fields(debug_value: Any) -> dict[str, Any]:
    if isinstance(debug_value, dict):
        return debug_value
    return {}


def resolve_single_game_starter(game: str, seat: int) -> str:
    if game == "ChineseStandardMahjong":
        return "llm" if seat in {0, 2} else "bl"
    if game == "FightTheLandlord":
        return "llm" if seat == 0 else "bl"
    return "llm" if seat == 0 else "bl"


def resolve_tournament_seat_owner(game: str, seat: int, llm1: str, llm2: str) -> str:
    if game == "ChineseStandardMahjong":
        return llm1 if seat in {0, 2} else llm2
    if game == "FightTheLandlord":
        return llm1 if seat == 0 else llm2
    return llm1 if seat == 0 else llm2


def split_tournament_pair(pair: str) -> tuple[str, str]:
    for name in sorted(KNOWN_TOURNAMENT_LLM_NAMES, key=len, reverse=True):
        prefix = f"{name}_"
        if not pair.startswith(prefix):
            continue
        other = pair[len(prefix) :]
        if other in KNOWN_TOURNAMENT_LLM_NAMES:
            return name, other
    raise ValueError(f"Cannot parse tournament pair: {pair}")


def parse_single_llm_meta(path: Path) -> dict[str, Any]:
    rel = path.relative_to(SINGLE_LLM_ROOT)
    game, level, llm_name = rel.parts[:3]
    stem_match = SINGLE_LLM_STEM_RE.match(path.stem)
    if not stem_match:
        raise ValueError(f"Unexpected single llm filename: {path.name}")
    round_token = stem_match.group("round")
    seat = int(stem_match.group("seat"))
    rematch = bool(stem_match.group("rematch"))
    starter = resolve_single_game_starter(game, seat)
    game_stem = f"{round_token}-{starter}{'-re' if rematch else ''}"
    game_log_path = SINGLE_GAME_ROOT / game / level / llm_name / f"{game_stem}.log"
    match_key = f"{game}-{level}-{llm_name}-{round_token}{'-re' if rematch else ''}"
    return {
        "mode": "single",
        "source_root": "log_llm_records",
        "game": game,
        "level": level,
        "llm_name": llm_name,
        "opponent_name": "baseline",
        "round": round_token,
        "round_token": round_token,
        "seat": seat,
        "is_rematch": rematch,
        "game_starter": starter,
        "match_key": match_key,
        "game_log_path": game_log_path,
        "game_log_stem": game_stem,
        "relative_log_path": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def parse_tournament_meta(path: Path) -> dict[str, Any]:
    rel = path.relative_to(TOURNAMENT_LLM_ROOT)
    game = rel.parts[0]
    stem_match = TOURNAMENT_LLM_STEM_RE.match(path.stem)
    if not stem_match:
        raise ValueError(f"Unexpected tournament llm filename: {path.name}")
    match_stem = stem_match.group("match_stem")
    seat = int(stem_match.group("seat"))
    match_match = TOURNAMENT_MATCH_RE.match(match_stem)
    if not match_match:
        raise ValueError(f"Unexpected tournament match stem: {match_stem}")
    pair = match_match.group("pair")
    round_token = match_match.group("round")
    llm1, llm2 = split_tournament_pair(pair)
    llm_name = resolve_tournament_seat_owner(game, seat, llm1, llm2)
    game_log_path = TOURNAMENT_GAME_ROOT / game / f"{match_stem}.log"
    match_key = f"{game}-{llm1}-vs-{llm2}-{round_token}"
    return {
        "mode": "tournament",
        "source_root": "log_llm_tournament_records",
        "game": game,
        "level": None,
        "llm_name": llm_name,
        "llm1_name": llm1,
        "llm2_name": llm2,
        "opponent_name": llm2 if llm_name == llm1 else llm1,
        "round": round_token,
        "round_token": round_token,
        "seat": seat,
        "is_rematch": "-re" in round_token,
        "match_key": match_key,
        "game_log_path": game_log_path,
        "game_log_stem": match_stem,
        "relative_log_path": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def load_game_payload(path: Path) -> Any:
    return json.loads(read_text(path))


def infer_state_actor(game: str, event: Any) -> int | None:
    if not isinstance(event, dict):
        return None
    if "round_idx" in event and isinstance(event.get("round_idx"), int):
        if game == "TexasHoldem2p":
            return event["round_idx"]
    return None


def is_player_action_event(event: Any) -> bool:
    if not isinstance(event, dict):
        return False
    action_name = event.get("action")
    if action_name in {"INIT", "DEAL", "DRAW"}:
        return False
    if "player" in event:
        return True
    if "round_idx" in event and "matchdata" in event and "final_result" not in event:
        return True
    return False


def build_game_event_record(
    *,
    dataset_kind: str,
    match_key: str,
    game: str,
    level: str | None,
    llm_name: str | None,
    round_token: str,
    event_index: int,
    event: Any,
    path: Path,
    extra: dict[str, Any],
) -> dict[str, Any]:
    actor_seat = None
    if isinstance(event, dict):
        actor_seat = event.get("player")
        if actor_seat is None:
            actor_seat = infer_state_actor(game, event)
    record_id = f"{match_key}-event-{event_index:05d}"
    return {
        "id": record_id,
        "dataset_kind": dataset_kind,
        "match_key": match_key,
        "game": game,
        "level": level,
        "llm_name": llm_name,
        "round": round_token,
        "event_index": event_index,
        "actor_seat": actor_seat,
        "event_type": (
            event.get("action") if isinstance(event, dict) else type(event).__name__
        ),
        "payload": event,
        "log_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        **extra,
    }


def build_game_index(
    root: Path,
    dataset_kind: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}

    for path in sorted(root.rglob("*.log")):
        try:
            payload = load_game_payload(path)
        except Exception as exc:
            print(f"[warn] Failed to parse game log {path}: {exc}")
            continue

        if root == SINGLE_GAME_ROOT:
            rel = path.relative_to(root)
            game, level, llm_name = rel.parts[:3]
            stem_match = SINGLE_GAME_STEM_RE.match(path.stem)
            if not stem_match:
                print(f"[warn] Unexpected single game filename: {path}")
                continue
            round_token = stem_match.group("round")
            rematch = bool(stem_match.group("rematch"))
            match_key = (
                f"{game}-{level}-{llm_name}-{round_token}{'-re' if rematch else ''}"
            )
            extra = {
                "mode": "single",
                "source_root": "log_game_records",
                "game_starter": stem_match.group("starter"),
                "is_rematch": rematch,
            }
        else:
            rel = path.relative_to(root)
            game = rel.parts[0]
            level = None
            llm_name = None
            match_match = TOURNAMENT_MATCH_RE.match(path.stem)
            if not match_match:
                print(f"[warn] Unexpected tournament game filename: {path}")
                continue
            pair = match_match.group("pair")
            round_token = match_match.group("round")
            try:
                llm1, llm2 = split_tournament_pair(pair)
            except ValueError as exc:
                print(f"[warn] {exc}")
                continue
            match_key = f"{game}-{llm1}-vs-{llm2}-{round_token}"
            extra = {
                "mode": "tournament",
                "source_root": "log_game_tournament_records",
                "llm1_name": llm1,
                "llm2_name": llm2,
                "is_rematch": "-re" in round_token,
            }

        events = payload if isinstance(payload, list) else [payload]
        candidate_events_by_seat: dict[int, list[int]] = {}
        game_records_for_file: list[dict[str, Any]] = []

        for idx, event in enumerate(events, start=1):
            record = build_game_event_record(
                dataset_kind=dataset_kind,
                match_key=match_key,
                game=game,
                level=level,
                llm_name=llm_name,
                round_token=round_token,
                event_index=idx,
                event=event,
                path=path,
                extra=extra,
            )
            records.append(record)
            game_records_for_file.append(record)

            if is_player_action_event(event):
                actor = record.get("actor_seat")
                if actor is not None:
                    candidate_events_by_seat.setdefault(int(actor), []).append(idx)

        index[str(path.resolve())] = {
            "records": game_records_for_file,
            "candidate_events_by_seat": candidate_events_by_seat,
            "record_ids_by_index": {
                record["event_index"]: record["id"] for record in game_records_for_file
            },
        }

    return records, index


def is_active_llm_record(record: ParsedLogRecord) -> bool:
    """
    判断 LLM 记录是否是有效的决策记录。

    有效记录必须有有效的游戏上下文（system_prompt 或 user_prompt）。

    判断标准（与 count_game_states.py 一致）：
    1. 有有效的 system_prompt（非空、非 'NA'、长度 >= 50）
    2. 或者有有效的 user_prompt（长度 >= 50）
    3. response 不是 PASSIVE_RESPONSES 中的值（但 PASS 本身是有效的游戏动作）

    注意：不再仅凭 active response 就判定为有效。
    一个有效的游戏决策状态必须有游戏上下文信息。
    """
    debug_fields = normalize_debug_fields(record.debug_value)
    response = record.response_value

    # 检查 system_prompt 是否有效
    system_prompt = debug_fields.get("system_prompt")
    if system_prompt:
        # 排除 'NA' 和太短的（无效的）
        if (
            isinstance(system_prompt, str)
            and system_prompt != "NA"
            and len(system_prompt) >= MIN_VALID_SYSTEM_PROMPT_LEN
        ):
            return True

    # 检查 user_prompt 是否有效
    user_prompt = debug_fields.get("user_prompt")
    if user_prompt:
        if (
            isinstance(user_prompt, str)
            and len(user_prompt) >= MIN_VALID_SYSTEM_PROMPT_LEN
        ):
            return True

    # 如果既没有有效的 system_prompt 也没有有效的 user_prompt，则不算有效记录
    # 注意：不再仅凭 active response 就判定为有效
    return False


def llm_record_id(match_key: str, seat: int, decision_index: int) -> str:
    return f"{match_key}-seat-{seat}-decision-{decision_index:05d}"


def build_llm_records(
    root: Path,
    game_index: dict[str, dict[str, Any]],
    dataset_kind: str,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    total_parsed = 0
    total_active = 0
    total_filtered = 0

    for path in sorted(root.rglob("*.log")):
        try:
            meta = (
                parse_single_llm_meta(path)
                if root == SINGLE_LLM_ROOT
                else parse_tournament_meta(path)
            )
        except Exception as exc:
            print(f"[warn] Failed to parse llm path {path}: {exc}")
            continue

        parsed_records = parse_llm_log(path)
        game_ref = game_index.get(str(meta["game_log_path"].resolve()))
        candidate_events = []
        if game_ref is not None:
            candidate_events = list(
                game_ref["candidate_events_by_seat"].get(meta["seat"], [])
            )
        candidate_cursor = 0

        for decision_index, parsed in enumerate(parsed_records, start=1):
            total_parsed += 1
            debug_fields = normalize_debug_fields(parsed.debug_value)

            # 关键修复：只有 is_active_llm_record 返回 True 的记录才保留
            if not is_active_llm_record(parsed):
                total_filtered += 1
                continue

            total_active += 1

            record: dict[str, Any] = {
                "id": llm_record_id(meta["match_key"], meta["seat"], total_active),
                "dataset_kind": dataset_kind,
                "mode": meta["mode"],
                "source_root": meta["source_root"],
                "match_key": meta["match_key"],
                "game": meta["game"],
                "level": meta["level"],
                "llm_name": meta["llm_name"],
                "opponent_name": meta["opponent_name"],
                "round": meta["round"],
                "seat": meta["seat"],
                "decision_index": total_active,  # 使用实际的有效决策索引
                "timestamp": parsed.timestamp,
                "system_prompt": debug_fields.get("system_prompt"),
                "user_prompt": debug_fields.get("user_prompt"),
                "reasoning": (
                    debug_fields.get("reasoning")
                    if debug_fields.get("reasoning") is not None
                    else debug_fields.get("reasoning_content")
                ),
                "output": debug_fields.get("output"),
                "response": parsed.response_value,
                "raw_debug": parsed.debug_raw,
                "raw_response": parsed.response_raw,
                "log_path": meta["relative_log_path"],
                "game_log_path": (
                    str(meta["game_log_path"].relative_to(ROOT)).replace("\\", "/")
                    if meta["game_log_path"].exists()
                    else None
                ),
                "game_log_stem": meta["game_log_stem"],
                "is_rematch": meta["is_rematch"],
                "game_event_index": None,
                "game_event_id": None,
            }

            if meta["mode"] == "single":
                record["game_starter"] = meta["game_starter"]
            else:
                record["llm1_name"] = meta["llm1_name"]
                record["llm2_name"] = meta["llm2_name"]

            # 关联到 game event
            if game_ref is not None and candidate_cursor < len(candidate_events):
                event_index = candidate_events[candidate_cursor]
                candidate_cursor += 1
                record["game_event_index"] = event_index
                record["game_event_id"] = game_ref["record_ids_by_index"].get(
                    event_index
                )

            if not dry_run:
                records.append(record)

    print(
        f"[stats] {root.name}: parsed={total_parsed}, active={total_active}, filtered={total_filtered}"
    )
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir.resolve()
    dry_run = args.dry_run

    print("=" * 60)
    print("Botzone Log to JSONL Converter (Fixed Version)")
    print("=" * 60)
    print(f"Output dir: {output_dir}")
    print(f"Dry run: {dry_run}")
    print()

    # Step 1: Build game index
    print("[1/4] Building game index (single)...")
    single_game_records, single_game_index = build_game_index(
        SINGLE_GAME_ROOT, "game_single"
    )
    print(f"  -> {len(single_game_records)} game events indexed")

    print("[2/4] Building game index (tournament)...")
    tournament_game_records, tournament_game_index = build_game_index(
        TOURNAMENT_GAME_ROOT, "game_tournament"
    )
    print(f"  -> {len(tournament_game_records)} tournament game events indexed")

    # Step 2: Build LLM records (with strict filtering)
    print("[3/4] Building LLM records (single)...")
    single_llm_records = build_llm_records(
        SINGLE_LLM_ROOT, single_game_index, "llm_single", dry_run=dry_run
    )
    print(f"  -> {len(single_llm_records)} valid LLM records")

    print("[4/4] Building LLM records (tournament)...")
    tournament_llm_records = build_llm_records(
        TOURNAMENT_LLM_ROOT, tournament_game_index, "llm_tournament", dry_run=dry_run
    )
    print(f"  -> {len(tournament_llm_records)} valid tournament LLM records")

    if dry_run:
        print("\n[Dry run] No files written.")
        return

    # Step 3: Write output
    print("\n[Output] Writing JSONL files...")
    write_jsonl(output_dir / "game_single_records.jsonl", single_game_records)
    write_jsonl(output_dir / "game_tournament_records.jsonl", tournament_game_records)
    write_jsonl(output_dir / "llm_single_records.jsonl", single_llm_records)
    write_jsonl(output_dir / "llm_tournament_records.jsonl", tournament_llm_records)

    summary = {
        "generated_at_root": str(ROOT).replace("\\", "/"),
        "output_dir": str(output_dir).replace("\\", "/"),
        "conversion_type": "filtered",
        "filter_rule": "is_active_llm_record with MIN_VALID_SYSTEM_PROMPT_LEN=50",
        "counts": {
            "game_single_records": len(single_game_records),
            "game_tournament_records": len(tournament_game_records),
            "llm_single_records": len(single_llm_records),
            "llm_tournament_records": len(tournament_llm_records),
        },
    }
    write_summary(output_dir / "conversion_summary.json", summary)

    print("\n" + "=" * 60)
    print("Summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
