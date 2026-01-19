import json
import sys
import re
import urllib.request
import urllib.error
import time
import random
import os
import collections
import itertools
import argparse
import requests

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

# --- Landlord Validator Logic Start ---

SUITS = ["♠", "♥", "♣", "♦"]
RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]


def get_card_rank(card_id):
    if card_id < 52:
        return card_id // 4
    elif card_id == 52:
        return 13
    elif card_id == 53:
        return 14
    return -1


def format_cards(ids):
    res = []
    sorted_ids = sorted(ids, key=lambda x: (get_card_rank(x), x))
    for c in sorted_ids:
        if c == 52:
            res.append("BlackJoker")
        elif c == 53:
            res.append("RedJoker")
        else:
            res.append(f"{SUITS[c%4]}{RANKS[c//4]}")
    return " ".join(res)


def check_poker_type(cards):
    """
    Returns: (type_name, length, main_rank_value)
    """
    l = len(cards)
    if l == 0:
        return "pass", l, -1

    d = collections.defaultdict(int)
    for i in cards:
        d[get_card_rank(i)] += 1

    cnt = sorted(d.values(), reverse=True)
    pattern = sorted(d.items(), key=lambda item: (item[1], item[0]), reverse=True)
    main = pattern[0][0]
    lcnt = len(cnt)
    points = sorted(d.keys(), reverse=True)

    if cnt == [1]:
        return "single", l, main
    if cnt == [2]:
        return "pair", l, main
    if cnt == [3]:
        return "triple", l, main
    if cnt == [3, 1]:
        return "triple_with_single", l, main
    if cnt == [3, 2]:
        return "triple_with_pair", l, main
    if cnt == [4]:
        return "bomb", l, main
    if cnt == [4, 1, 1]:
        return "four_with_single", l, main
    if cnt == [4, 2, 2]:
        return "four_with_pair", l, main
    if points == [14, 13]:
        return "rocket", l, main

    # Straight
    if (
        cnt[0] == cnt[-1] == 1
        and lcnt >= 5
        and points[0] - points[-1] == l - 1
        and main <= 11
    ):
        return "straight", l, main

    # Pair Straight
    if (
        cnt[0] == cnt[-1] == 2
        and lcnt >= 3
        and points[0] - points[-1] == lcnt - 1
        and main <= 11
    ):
        return "pair_straight", l, main

    # Airplane
    if cnt[0] == cnt[-1] == 3 and points[0] - points[-1] == lcnt - 1 and main <= 11:
        return "airplane", l, main

    # Airplane with Single
    if l % 4 == 0:
        k = l // 4
        triplets = [r for r, c in d.items() if c >= 3]
        triplets.sort(reverse=True)
        for i in range(len(triplets) - k + 1):
            sub = triplets[i : i + k]
            if sub[0] - sub[-1] == k - 1 and sub[0] <= 11:
                return "airplane_with_single", l, sub[0]

    # Airplane with Pair
    if l % 5 == 0:
        k = l // 5
        triplets = [r for r, c in d.items() if c >= 3]
        triplets.sort(reverse=True)
        for i in range(len(triplets) - k + 1):
            sub = triplets[i : i + k]
            if sub[0] - sub[-1] == k - 1 and sub[0] <= 11:
                rem_d = d.copy()
                for r in sub:
                    rem_d[r] -= 3
                is_valid_wings = True
                for r, c in rem_d.items():
                    if c == 0:
                        continue
                    if c != 2 and c != 4:
                        is_valid_wings = False
                        break
                if is_valid_wings:
                    return "airplane_with_pair", l, sub[0]

    return "invalid", 0, 0


def find_moves(hand_ids, target_type=None, target_len=0, target_rank=-1):
    valid_moves = []

    # Group by rank
    rank_map = collections.defaultdict(list)
    for cid in hand_ids:
        rank_map[get_card_rank(cid)].append(cid)

    unique_ranks = sorted(rank_map.keys())

    # Always check Bombs/Rockets
    if 52 in hand_ids and 53 in hand_ids:
        if target_type != "rocket":
            valid_moves.append(([52, 53], "rocket", 14))

    for r in unique_ranks:
        if len(rank_map[r]) == 4:
            if target_type == "rocket":
                continue
            if target_type == "bomb" and r <= target_rank:
                continue
            valid_moves.append((rank_map[r], "bomb", r))

    if target_type == "rocket":
        return valid_moves

    # If Free Play (target_type is None or "pass"), generate ALL valid moves of ALL types
    search_types = []
    if not target_type or target_type == "pass":
        search_types = [
            "single",
            "pair",
            "triple",
            "triple_with_single",
            "triple_with_pair",
            "straight",
            "pair_straight",
            "airplane",
            "airplane_with_single",
            "airplane_with_pair",
            "four_with_single",
            "four_with_pair",
            "bomb",
            "rocket",
        ]
    else:
        search_types = [target_type]

    for current_type in search_types:
        if current_type == "single":
            for r in unique_ranks:
                if target_type == "single" and r <= target_rank:
                    continue
                valid_moves.append((rank_map[r][:1], "single", r))

        elif current_type == "pair":
            for r in unique_ranks:
                if len(rank_map[r]) >= 2:
                    if target_type == "pair" and r <= target_rank:
                        continue
                    valid_moves.append((rank_map[r][:2], "pair", r))

        elif current_type == "triple":
            for r in unique_ranks:
                if len(rank_map[r]) >= 3:
                    if target_type == "triple" and r <= target_rank:
                        continue
                    valid_moves.append((rank_map[r][:3], "triple", r))

        elif current_type == "triple_with_single":
            for r in unique_ranks:
                if len(rank_map[r]) >= 3:
                    if target_type == "triple_with_single" and r <= target_rank:
                        continue
                    base = rank_map[r][:3]
                    for other_r in unique_ranks:
                        if other_r == r:
                            continue
                        if len(rank_map[other_r]) >= 1:
                            valid_moves.append(
                                (base + rank_map[other_r][:1], "triple_with_single", r)
                            )

        elif current_type == "triple_with_pair":
            for r in unique_ranks:
                if len(rank_map[r]) >= 3:
                    if target_type == "triple_with_pair" and r <= target_rank:
                        continue
                    base = rank_map[r][:3]
                    for other_r in unique_ranks:
                        if other_r == r:
                            continue
                        if len(rank_map[other_r]) >= 2:
                            valid_moves.append(
                                (base + rank_map[other_r][:2], "triple_with_pair", r)
                            )

        elif current_type == "straight":
            min_len = 5 if (not target_type or target_type == "pass") else target_len
            max_len = 12
            check_lengths = (
                [target_len]
                if target_type == "straight"
                else range(min_len, max_len + 1)
            )

            for length in check_lengths:
                for i in range(len(unique_ranks)):
                    start_r = unique_ranks[i]
                    if start_r > 11:
                        break
                    if i + length > len(unique_ranks):
                        break

                    window = unique_ranks[i : i + length]
                    if window[-1] - window[0] == length - 1 and window[-1] <= 11:
                        if target_type == "straight" and window[-1] <= target_rank:
                            continue

                        cards = []
                        for wr in window:
                            cards.append(rank_map[wr][0])
                        valid_moves.append((cards, "straight", window[-1]))

        elif current_type == "pair_straight":
            min_seq_len = 3
            check_seq_lens = []
            if target_type == "pair_straight":
                check_seq_lens = [target_len // 2]
            elif not target_type or target_type == "pass":
                check_seq_lens = range(min_seq_len, 13)

            for seq_len in check_seq_lens:
                for i in range(len(unique_ranks)):
                    start_r = unique_ranks[i]
                    if start_r > 11:
                        break
                    if i + seq_len > len(unique_ranks):
                        break
                    window = unique_ranks[i : i + seq_len]
                    if window[-1] - window[0] == seq_len - 1 and window[-1] <= 11:
                        if target_type == "pair_straight" and window[0] <= target_rank:
                            continue
                        if all(len(rank_map[r]) >= 2 for r in window):
                            cards = []
                            for wr in window:
                                cards.extend(rank_map[wr][:2])
                            valid_moves.append((cards, "pair_straight", window[0]))

        elif current_type == "airplane":
            min_seq_len = 2
            check_seq_lens = []
            if target_type == "airplane":
                check_seq_lens = [target_len // 3]
            elif not target_type or target_type == "pass":
                check_seq_lens = range(min_seq_len, 13)

            for seq_len in check_seq_lens:
                for i in range(len(unique_ranks)):
                    start_r = unique_ranks[i]
                    if start_r > 11:
                        break
                    if i + seq_len > len(unique_ranks):
                        break
                    window = unique_ranks[i : i + seq_len]
                    if window[-1] - window[0] == seq_len - 1 and window[-1] <= 11:
                        if target_type == "airplane" and window[0] <= target_rank:
                            continue
                        if all(len(rank_map[r]) >= 3 for r in window):
                            cards = []
                            for wr in window:
                                cards.extend(rank_map[wr][:3])
                            valid_moves.append((cards, "airplane", window[0]))

        elif current_type == "four_with_single":
            for r in unique_ranks:
                if len(rank_map[r]) >= 4:
                    if target_type == "four_with_single" and r <= target_rank:
                        continue
                    base = rank_map[r][:4]
                    other_ranks = [or_ for or_ in unique_ranks if or_ != r]
                    if len(other_ranks) >= 2:
                        k1 = other_ranks[0]
                        k2 = other_ranks[1]
                        valid_moves.append(
                            (
                                base + rank_map[k1][:1] + rank_map[k2][:1],
                                "four_with_single",
                                r,
                            )
                        )

        elif current_type == "four_with_pair":
            for r in unique_ranks:
                if len(rank_map[r]) >= 4:
                    if target_type == "four_with_pair" and r <= target_rank:
                        continue
                    base = rank_map[r][:4]
                    other_pairs = [
                        or_
                        for or_ in unique_ranks
                        if or_ != r and len(rank_map[or_]) >= 2
                    ]
                    if len(other_pairs) >= 2:
                        k1 = other_pairs[0]
                        k2 = other_pairs[1]
                        valid_moves.append(
                            (
                                base + rank_map[k1][:2] + rank_map[k2][:2],
                                "four_with_pair",
                                r,
                            )
                        )

    return valid_moves


# --- Landlord Validator Logic End ---


def reconstruct_game_history(requests_hist, responses_hist):
    """
    Reconstructs the game history from Botzone requests/responses lists.
    Returns:
        history_log (list of str): Narrative log lines.
        seen_cards (Counter): Count of every card ID seen played.
    """
    history_log = []
    seen_cards = collections.Counter()

    for i in range(len(responses_hist) + 1):
        if i >= len(requests_hist):
            break

        opponents_moves = requests_hist[i].get("history", [[], []])
        round_num = i + 1

        # Next Player (Right)
        next_move = opponents_moves[0]
        if next_move:
            history_log.append(
                f"Turn {round_num} (Next Player): {format_cards(next_move)}"
            )
            for c in next_move:
                seen_cards[c] += 1
        elif i > 0:
            history_log.append(f"Turn {round_num} (Next Player): Pass")

        # Prev Player (Left)
        prev_move = opponents_moves[1]
        if prev_move:
            history_log.append(
                f"Turn {round_num} (Prev Player): {format_cards(prev_move)}"
            )
            for c in prev_move:
                seen_cards[c] += 1
        elif i > 0:
            history_log.append(f"Turn {round_num} (Prev Player): Pass")

        if i < len(responses_hist):
            my_move = responses_hist[i]
            if my_move:
                history_log.append(f"Turn {round_num} (You): {format_cards(my_move)}")
                for c in my_move:
                    seen_cards[c] += 1
            else:
                history_log.append(f"Turn {round_num} (You): Pass")

    return history_log, seen_cards


def calculate_unknown_cards(my_hand, seen_cards):
    total_deck = list(range(54))
    my_hand_set = set(my_hand)
    unknown_ids = []

    for c in total_deck:
        if c in my_hand_set:
            continue
        if seen_cards[c] > 0:
            continue
        unknown_ids.append(c)

    rank_counts = collections.defaultdict(int)
    for c in unknown_ids:
        rank_counts[get_card_rank(c)] += 1

    output_parts = []
    for r in range(14, -1, -1):
        count = rank_counts[r]
        if count > 0:
            rank_str = ""
            if r == 14:
                rank_str = "RedJoker"
            elif r == 13:
                rank_str = "BlackJoker"
            else:
                rank_str = RANKS[r]
            output_parts.append(f"{rank_str}: {count}")

    return ", ".join(output_parts)


def parse_llm_response(content):
    # First try to find a JSON object in the "Answer: " section if it exists
    answer_match = re.search(r"Answer:\s*(\{.*\})", content, re.DOTALL)
    if answer_match:
        try:
            return json.loads(answer_match.group(1))
        except:
            pass

    # Fallback to finding the last JSON object in the text
    # Finding ALL matches and taking the last one is safer if Explanation contains braces
    matches = re.findall(r"\{.*?\}", content, re.DOTALL)
    if matches:
        # Iterate backwards to find the first valid JSON
        for m in reversed(matches):
            try:
                # We need to make sure it looks like our expected JSON (has "cards" key)
                j = json.loads(m)
                if "cards" in j:
                    return j
            except:
                continue

    return None


def main():
    access_mode, model_name = access_mode_and_llm()
    if access_mode == "local_vllm":
        api_base, api_key, query_api = local_vllm_info()
    elif access_mode == "silicon_flow":
        api_base, api_key, query_api = silicon_flow_info()
    elif access_mode == "lab_openai_foreign":
        api_base, api_key, query_api = openai_foreign_info()
    elif access_mode == "lab_openai_chinese":
        api_base, api_key, query_api = openai_chinese_info()

    # Read Input
    try:
        # Check if stdin has data
        if sys.stdin.isatty():
            # Running interactively without input, maybe just testing args?
            # But in Botzone, we expect JSON from stdin.
            # If no input, just return or print help?
            # Let's assume input might come.
            pass

        line = sys.stdin.read()
        if not line:
            return
        full_input = json.loads(line)
    except:
        return

    # Extract Game State
    requests_hist = full_input.get("requests", [])
    responses_hist = full_input.get("responses", [])

    if not requests_hist:
        return

    current_request = requests_hist[-1]

    # Calculate Current Hand
    initial_hand = requests_hist[0]["own"]
    current_hand = list(initial_hand)
    for resp in responses_hist:
        for card in resp:
            if card in current_hand:
                current_hand.remove(card)

    # History of plays
    history = current_request.get("history", [[], []])

    # Calculate Card Counts of Other Players
    # Botzone protocol: "publiccard" contains initially revealed landlord cards.
    # But usually, we just know everyone starts with 17 (Farmer) or 20 (Landlord).
    # Since we are playing, we can deduce from history?
    # Actually, simpler: we can count how many cards each player has played.
    # Player 0 (Landlord): Starts with 20
    # Player 1 (Farmer): Starts with 17
    # Player 2 (Farmer): Starts with 17
    # We need to know who we are.
    # In Botzone single bot mode, we are usually Player 0, 1, or 2.
    # But the request doesn't explicitly tell us our ID in 'request' field easily?
    # Wait, 'own' is our hand.
    # But for opponent card counts, we need to track turns.

    # A simplified approach: Just use the info if provided, or estimate.
    # Standard Botzone doesn't explicitly give opponent hand sizes in the request JSON for simpleio?
    # Let's check 'public' or 'globaldata' if we were tracking.
    # But without tracking, we can only see history.

    # Let's assume standard game:
    # We can infer our position relative to history.
    # history[0] is prev-prev player, history[1] is prev player.
    # If we are Landlord (20 cards), others are Farmers (17).
    # If we are Farmer, one is Landlord (20), one is Farmer (17).
    # Who is who?
    # The 'publiccard' field in request usually implies who is landlord?
    # Actually, standard Dou Dizhu: Landlord is revealed at start.
    # In this simplified bot, we might not know exactly without full history tracking.

    # HOWEVER, we can provide a "Cards Remaining Unknown" which helps.
    # The user specifically asked for "number of cards left in the other 2 player's hand".
    # This requires state tracking across turns, which is hard in a stateless bot (unless we use globaldata).
    # But Botzone request includes FULL history?
    # No, request["history"] only has the last 2 moves.
    # request["requests"] (history list) has ALL previous requests if we are using full history?
    # Yes, `requests_hist` has all past requests.

    # Let's calculate cards played by each player relative to us.
    # We are "Player Me".
    # Next Player (Right)
    # Prev Player (Left)

    cards_played_next = 0
    cards_played_prev = 0

    # Iterate through all history to count cards played by others
    # requests_hist is a list of requests we received.
    # responses_hist is a list of responses we made.

    # Turn 1: We receive Request 1. It might contain initial history?
    # Actually, Request i contains the moves made by others SINCE our last move.
    # So Request i's "history" field:
    # history[0]: Move by player (Me - 2) % 3  -> Next Player (if we go anticlockwise? No)
    # Standard order: Landlord -> Farmer 1 -> Farmer 2
    # Let's assume standard: Next is Right, Prev is Left.

    for req in requests_hist:
        h = req.get("history", [[], []])
        # h[0] is the move by the player before the player before me?
        # Actually, Botzone doc says:
        # history[0]: move of the player before the player before you (i.e. next next player = next player)
        # history[1]: move of the player before you (prev player)

        # Next Player (Right) is history[0]
        if h[0]:
            cards_played_next += len(h[0])

        # Prev Player (Left) is history[1]
        if h[1]:
            cards_played_prev += len(h[1])

    # Determine initial counts
    # We need to know who is Landlord.
    # Usually, the one who has the extra 3 cards is Landlord.
    # request["publiccard"] exists if we are NOT landlord? Or always?
    # If we have 20 cards initially, we are Landlord.
    # If we have 17, one of opponents is Landlord.

    my_initial_count = len(initial_hand)

    # Default assumptions
    next_initial = 17
    prev_initial = 17

    # Check for public cards (usually 3 cards)
    public_cards = full_input.get("publiccard", [])

    # Heuristic to identify Landlord
    if my_initial_count == 20:
        # I am Landlord
        next_initial = 17
        prev_initial = 17
    else:
        # I am Peasant. One of them is Landlord.
        # But who?
        # In Botzone, Landlord plays first.
        # If I am Player 1 (Peasant), Landlord (Player 0) is Prev (Left).
        # If I am Player 2 (Peasant), Landlord (Player 0) is Next (Right)? (Player 2 -> 0 -> 1)
        # Wait, order is 0 -> 1 -> 2 -> 0 ...
        # If I am 1: Prev is 0 (Landlord), Next is 2 (Peasant)
        # If I am 2: Prev is 1 (Peasant), Next is 0 (Landlord)

        # We can try to deduce from the first request.
        # If first request has history[1] (Prev played), then Prev moved before me.
        # If first request has history[0] empty and history[1] empty? Then I moved first? (Landlord)

        first_req_hist = requests_hist[0].get("history", [[], []])

        if not first_req_hist[0] and not first_req_hist[1]:
            # I went first -> Landlord (Handled by my_initial_count == 20 check)
            pass
        elif first_req_hist[1] and not first_req_hist[0]:
            # Prev moved, Next didn't. Order: Prev -> Me -> Next
            # So Prev is Landlord.
            prev_initial = 20
        elif first_req_hist[0] and not first_req_hist[1]:
            # Next moved, Prev didn't (or passed).
            # Order: Next -> Prev -> Me
            # So Next is Landlord.
            next_initial = 20
        elif first_req_hist[0] and first_req_hist[1]:
            # Both moved. Order: Next -> Prev -> Me?
            # No, standard history is [NextPlayerMove, PrevPlayerMove]
            # Wait, history definition:
            # history[0]: Move of "Next Player" (The one who plays AFTER me? No, the one who played 2 turns ago)
            # Let's stick to: history[0] = Right (Next), history[1] = Left (Prev)
            # If I am Player 2. Player 0 (Landlord) played. Player 1 played.
            # Then it's my turn.
            # Player 1 is Prev (Left). Player 0 is Next (Right).
            # So Next is Landlord.
            next_initial = 20

    next_left = next_initial - cards_played_next
    prev_left = prev_initial - cards_played_prev

    # --- End Calculation ---

    # Analyze Last Move
    last_move = []
    last_mover_type = "free"  # or "beat"

    if history[1]:  # Immediate previous player
        last_move = history[1]
        last_mover_type = "beat"
    elif history[0]:  # Pre-previous (if immediate passed)
        last_move = history[0]
        last_mover_type = "beat"
    else:
        last_mover_type = "free"

    last_type_name = "pass"
    last_len = 0
    last_rank = -1
    if last_mover_type == "beat":
        last_type_name, last_len, last_rank = check_poker_type(last_move)

    # Generate Valid Moves
    valid_moves_tuples = find_moves(
        current_hand,
        target_type=last_type_name if last_mover_type == "beat" else "pass",
        target_len=last_len,
        target_rank=last_rank,
    )

    # quick response if only one move
    if len(valid_moves_tuples) == 0:
        print(
            json.dumps(
                {
                    "response": [],
                    "debug": {
                        "system_prompt": "NA",
                        "user_prompt": "NA",
                        "reasoning": "NA",
                        "output": "Auto response if only one move (Pass).",
                    },
                }
            )
        )
        return

    # Format Valid Moves for LLM
    valid_moves_str_list = []
    # Sort nicely: Bomb/Rocket last, others by type
    valid_moves_tuples.sort(
        key=lambda x: (x[1] == "rocket", x[1] == "bomb", x[1], x[2])
    )

    for cards, type_name, rank in valid_moves_tuples:
        valid_moves_str_list.append(f"{type_name}: {format_cards(cards)}")

    if last_mover_type != "free":
        valid_moves_str_list.append("pass: []")

    # Limit validation text length to avoid context overflow/confusion
    # display_limit = 30
    # if len(valid_moves_str_list) > display_limit:
    #     valid_moves_display = "\n".join(valid_moves_str_list[:display_limit]) + f"\n... (+{len(valid_moves_str_list)-display_limit} more valid moves)"
    # else:
    valid_moves_display = "\n".join(valid_moves_str_list)

    if not valid_moves_tuples:
        valid_moves_display = "No valid moves available. You must PASS."

    # Construct Game History
    history_log, seen_cards = reconstruct_game_history(requests_hist, responses_hist)
    history_log_str = "\n".join(
        history_log[-15:]
    )  # Keep last 15 entries to avoid clutter
    if not history_log_str:
        history_log_str = "No history yet."

    unknown_cards_str = calculate_unknown_cards(current_hand, seen_cards)

    # Construct System Prompt
    role_description = "the landlord" if my_initial_count == 20 else "a peasant"
    role_objective = (
        "The landlord's aim is to be the first to play out all his cards in valid combinations. If any of the other players manages to play all their cards before the landlord, you lose."
        if my_initial_count == 20
        else "Your aim is to be the play out all your cards before the landlord does, OR help your teammate (the other peasant) play out their cards before the landlord does. If the landlord plays out all cards first, you lose."
    )

    # Determine Opponent Roles for Display
    next_role_label = ""
    prev_role_label = ""
    my_player_id_ = "Unknown"
    teammate_info = ""

    if my_initial_count == 20:
        # I am Landlord
        my_player_id_ = "0"
        next_role_label = "Peasant (Opponent)"
        prev_role_label = "Peasant (Opponent)"
        teammate_info = "You are the Landlord. Both the Next Player (Right) and the Previous Player (Left) are Peasants and are your ENEMIES. You fight alone. The objective is to empty your hand as fast as possible."
    else:
        # I am Peasant
        if prev_initial == 20:
            # Prev is Landlord
            my_player_id_ = "1"
            prev_role_label = "Landlord (Opponent)"
            next_role_label = "Peasant (Teammate)"
            teammate_info = "You are a Peasant. The Previous Player (Left) is the Landlord (ENEMY). The Next Player (Right) is your TEAMMATE (Peasant). You must cooperate with your teammate to beat the Landlord. The objective is to empty your hand before the landlord does, or help your teammate empty their hand before the landlord does."
        elif next_initial == 20:
            # Next is Landlord
            my_player_id_ = "2"
            next_role_label = "Landlord (Opponent)"
            prev_role_label = "Peasant (Teammate)"
            teammate_info = "You are a Peasant. The Next Player (Right) is the Landlord (ENEMY). The Previous Player (Left) is your TEAMMATE (Peasant). You must cooperate with your teammate to beat the Landlord. The objective is to empty your hand before the landlord does, or help your teammate empty their hand before the landlord does."
        else:
            # Fallback/Uncertain
            next_role_label = "Unknown"
            prev_role_label = "Unknown"

    system_prompt = """
        You are a Fight The Landlord (Dou Dizhu) player. 
        ### Introduction
        Fight the Landlord (Dou Dizhu) is a poker climbing game primarily for three players.
        ### Players, Cards and Deal
        This game uses a 54-card pack including two jokers, red and black. The cards rank from high to low:
        red joker, black joker, 2, A, K, Q, J, 10, 9, 8, 7, 6, 5, 4, 3. Suits are irrelevant.

        ### Play
        The landlord plays first, and may play a single card or any legal combination.
        Each subsequent player in anticlockwise order must either pass (play no card) or beat the previous play
        by playing a higher combination of the same number of cards and same type.
        There are just two exceptions to this: a rocket can beat any combination, and a bomb can beat any combination
        except a higher bomb or rocket.

        ### Combinations
        1. Single card: ranking from three (low) up to red joker (high).
        2. Pair: two cards of the same rank, from three (low) up to two (high).
        3. Triplet: three cards of the same rank.
        4. Triplet with an attached card: a triplet with any single card added.
        5. Triplet with an attached pair: a triplet with a pair added.
        6. Sequence: at least five cards of consecutive rank, from 3 up to ace. Twos and jokers cannot be used.
        7. Sequence of pairs: at least three pairs of consecutive ranks, from 3 up to ace. Twos and jokers cannot be used.
        8. Sequence of triplets: at least two triplets of consecutive ranks from three up to ace.
        9. Sequence of triplets with attached cards: an extra card is added to each triplet.
        10. Sequence of triplets with attached pairs: an extra pair is attached to each triplet.
        11. Bomb: four cards of the same rank. Beats everything except a rocket and a higher bomb.
        12. Rocket: a pair of jokers. The highest combination, beats everything.
        13. Quadplex set: a quad with two single cards OR two pairs attached.
        Use the EXACT card symbols provided in the Valid Moves list.
        Prepare a valid JSON object like {"cards": ["♠3", "♥3"]} for your answer, along with your explanation and reason. If you pass, output: {"cards": []}
        
        Now is your turn, to your best ability, choose your move to maximize your chances of winning.
        Please briefly evaluate a few proimsing moves, provide reason for your final choice, and output the action with specified format.
        Your response format should be:
        Evaluation: [Your Evaluation]
        Reason: [Your Reason]
        Answer: [Your Answer]
    """
    hand_str = format_cards(current_hand)
    last_play_str = (
        format_cards(last_move) if last_mover_type == "beat" else "None (Free Play)"
    )

    state_prompt = (
        f"You are playing as {role_description}. {role_objective}\n"
        f"{teammate_info}\n\n"
        f"Your Hand: {hand_str}\n"
        f"Last Play to Beat: {last_play_str}\n"
        f"--- Game History (Recent) ---\n{history_log_str}\n"
        f"--- Player Info ---\n"
        f"Cards Held by Next Player (Right) [{next_role_label}]: {next_left}\n"
        f"Cards Held by Prev Player (Left) [{prev_role_label}]: {prev_left}\n"
        f"--- Cards Remaining Unknown (Card Counting) ---\n"
        f"(Format explanation: 'Rank: Count', e.g., '2: 4' means there are four 2s left unknown)\n"
        f"{unknown_cards_str}\n"
        f"Valid Moves:\n{valid_moves_display}\n\n"
        "Select the best move from the Valid Moves list above. You can choose to pass even if you have valid moves that can beat the previous play, but you cannot pass if you are in a Free Play (no last play).\n"
        "Ensure your response matches one of the valid moves exactly.\n"
        "Remember to provide Explanation, Reason, and Answer."
    )

    # Retry Loop
    max_retries = 3
    final_response = []
    error_prompt = ""
    for attempt in range(max_retries):
        user_prompt = state_prompt + error_prompt
        content, reasoning_text = query_api(
            api_base,
            api_key,
            model_name,
            system_prompt,
            user_prompt,
        )

        # Parse
        parsed = parse_llm_response(content)
        played_cards_symbols = []
        if parsed and "cards" in parsed:
            played_cards_symbols = parsed["cards"]
        else:
            error_prompt = (
                'Invalid format. Please output strictly JSON: {"cards": [...]}',
            )

        # Map Symbols to IDs
        symbol_to_id = {}
        for cid in current_hand:
            s = format_cards([cid])
            symbol_to_id[s] = cid

        played_ids = []
        parse_error = False
        failed_symbol = ""
        for s in played_cards_symbols:
            s = s.strip()
            if s in symbol_to_id:
                played_ids.append(symbol_to_id[s])
            else:
                parse_error = True
                failed_symbol = s
                break

        if parse_error:
            error_prompt = f"Invalid card symbol: '{failed_symbol}'. Use exact symbols from Your Hand."

        # Validate Move Logic
        if not played_ids:
            if last_mover_type == "free":
                error_prompt = "You cannot pass on a Free Play. You must play something from the Valid Moves list."
                continue
            else:
                final_response = []  # Pass
                break

        # Check against valid_moves_tuples
        is_valid = False
        played_ids_sorted = sorted(played_ids)

        for v_ids, _, _ in valid_moves_tuples:
            if sorted(v_ids) == played_ids_sorted:
                is_valid = True
                break

        if is_valid:
            final_response = played_ids
            break
        else:
            error_prompt = f"Invalid move. Your play {played_cards_symbols} is not in the Valid Moves list. Please choose one from the list."

    # Fallback if failed
    # if not final_response and last_mover_type == "free" and valid_moves_tuples:
    #     # If we failed to get a valid move on free play, just pick the smallest valid move (heuristic)
    #     # valid_moves_tuples is sorted by rank loosely, pick first
    #     final_response = valid_moves_tuples[0][0]
    #     debug_log.append("Fallback: Picked first valid move.")

    print(
        json.dumps(
            {
                "response": final_response,
                "debug": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "reasoning": reasoning_text,
                    "output": content,
                },
            }
        )
    )


if __name__ == "__main__":
    main()
