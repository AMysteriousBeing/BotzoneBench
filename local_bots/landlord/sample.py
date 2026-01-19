import json
import sys
import collections
import random

# --- Landlord Validator Logic Start ---

SUITS = ['♠', '♥', '♣', '♦']
RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']

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
        if c == 52: res.append("BlackJoker")
        elif c == 53: res.append("RedJoker")
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

    if cnt == [1]: return "single", l, main
    if cnt == [2]: return "pair", l, main
    if cnt == [3]: return "triple", l, main
    if cnt == [3, 1]: return "triple_with_single", l, main
    if cnt == [3, 2]: return "triple_with_pair", l, main
    if cnt == [4]: return "bomb", l, main
    if cnt == [4, 1, 1]: return "four_with_single", l, main
    if cnt == [4, 2, 2]: return "four_with_pair", l, main
    if points == [14, 13]: return "rocket", l, main
    
    # Straight
    if cnt[0] == cnt[-1] == 1 and lcnt >= 5 and points[0] - points[-1] == l - 1 and main <= 11:
        return "straight", l, main
    
    # Pair Straight
    if cnt[0] == cnt[-1] == 2 and lcnt >= 3 and points[0] - points[-1] == lcnt - 1 and main <= 11:
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
            sub = triplets[i : i+k]
            if sub[0] - sub[-1] == k - 1 and sub[0] <= 11:
                return "airplane_with_single", l, sub[0]

    # Airplane with Pair
    if l % 5 == 0:
        k = l // 5
        triplets = [r for r, c in d.items() if c >= 3]
        triplets.sort(reverse=True)
        for i in range(len(triplets) - k + 1):
            sub = triplets[i : i+k]
            if sub[0] - sub[-1] == k - 1 and sub[0] <= 11:
                rem_d = d.copy()
                for r in sub: rem_d[r] -= 3
                is_valid_wings = True
                for r, c in rem_d.items():
                    if c == 0: continue
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
            if target_type == "rocket": continue
            if target_type == "bomb" and r <= target_rank: continue
            valid_moves.append((rank_map[r], "bomb", r))
            
    if target_type == "rocket": return valid_moves
    
    # If Free Play (target_type is None or "pass"), generate ALL valid moves of ALL types
    search_types = []
    if not target_type or target_type == "pass":
        search_types = ["single", "pair", "triple", "triple_with_single", "triple_with_pair", "straight", "pair_straight", "airplane", "airplane_with_single", "airplane_with_pair", "four_with_single", "four_with_pair", "bomb", "rocket"]
    else:
        search_types = [target_type]

    for current_type in search_types:
        if current_type == "single":
            for r in unique_ranks:
                if target_type == "single" and r <= target_rank: continue
                valid_moves.append((rank_map[r][:1], "single", r))
                    
        elif current_type == "pair":
            for r in unique_ranks:
                if len(rank_map[r]) >= 2:
                    if target_type == "pair" and r <= target_rank: continue
                    valid_moves.append((rank_map[r][:2], "pair", r))
                    
        elif current_type == "triple":
            for r in unique_ranks:
                if len(rank_map[r]) >= 3:
                    if target_type == "triple" and r <= target_rank: continue
                    valid_moves.append((rank_map[r][:3], "triple", r))
        
        elif current_type == "triple_with_single":
            for r in unique_ranks:
                if len(rank_map[r]) >= 3:
                    if target_type == "triple_with_single" and r <= target_rank: continue
                    base = rank_map[r][:3]
                    for other_r in unique_ranks:
                        if other_r == r: continue
                        if len(rank_map[other_r]) >= 1:
                            valid_moves.append((base + rank_map[other_r][:1], "triple_with_single", r))
                        
        elif current_type == "triple_with_pair":
            for r in unique_ranks:
                if len(rank_map[r]) >= 3:
                    if target_type == "triple_with_pair" and r <= target_rank: continue
                    base = rank_map[r][:3]
                    for other_r in unique_ranks:
                        if other_r == r: continue
                        if len(rank_map[other_r]) >= 2:
                            valid_moves.append((base + rank_map[other_r][:2], "triple_with_pair", r))
                            
        elif current_type == "straight":
            min_len = 5 if (not target_type or target_type == "pass") else target_len
            max_len = 12 
            check_lengths = [target_len] if target_type == "straight" else range(min_len, max_len + 1)
            
            for length in check_lengths:
                for i in range(len(unique_ranks)):
                    start_r = unique_ranks[i]
                    if start_r > 11: break
                    if i + length > len(unique_ranks): break
                    
                    window = unique_ranks[i : i+length]
                    if window[-1] - window[0] == length - 1 and window[-1] <= 11:
                        if target_type == "straight" and window[-1] <= target_rank: continue
                        
                        cards = []
                        for wr in window:
                            cards.append(rank_map[wr][0])
                        valid_moves.append((cards, "straight", window[-1]))

        elif current_type == "pair_straight":
            min_len = 6 if (not target_type or target_type == "pass") else target_len
            seq_len = min_len // 2
            
            for i in range(len(unique_ranks)):
                start_r = unique_ranks[i]
                if start_r > 11: break
                if i + seq_len > len(unique_ranks): break
                window = unique_ranks[i : i+seq_len]
                if window[-1] - window[0] == seq_len - 1 and window[-1] <= 11:
                    if target_type == "pair_straight" and window[0] <= target_rank: continue
                    if all(len(rank_map[r]) >= 2 for r in window):
                        cards = []
                        for wr in window:
                            cards.extend(rank_map[wr][:2])
                        valid_moves.append((cards, "pair_straight", window[0]))

        elif current_type == "airplane":
            min_len = 6 if (not target_type or target_type == "pass") else target_len
            seq_len = min_len // 3
            
            for i in range(len(unique_ranks)):
                start_r = unique_ranks[i]
                if start_r > 11: break
                if i + seq_len > len(unique_ranks): break
                window = unique_ranks[i : i+seq_len]
                if window[-1] - window[0] == seq_len - 1 and window[-1] <= 11:
                    if target_type == "airplane" and window[0] <= target_rank: continue
                    if all(len(rank_map[r]) >= 3 for r in window):
                        cards = []
                        for wr in window:
                            cards.extend(rank_map[wr][:3])
                        valid_moves.append((cards, "airplane", window[0]))

        elif current_type == "four_with_single":
            for r in unique_ranks:
                if len(rank_map[r]) >= 4:
                    if target_type == "four_with_single" and r <= target_rank: continue
                    base = rank_map[r][:4]
                    other_ranks = [or_ for or_ in unique_ranks if or_ != r]
                    if len(other_ranks) >= 2:
                        k1 = other_ranks[0]
                        k2 = other_ranks[1]
                        valid_moves.append((base + rank_map[k1][:1] + rank_map[k2][:1], "four_with_single", r))

        elif current_type == "four_with_pair":
            for r in unique_ranks:
                if len(rank_map[r]) >= 4:
                    if target_type == "four_with_pair" and r <= target_rank: continue
                    base = rank_map[r][:4]
                    other_pairs = [or_ for or_ in unique_ranks if or_ != r and len(rank_map[or_]) >= 2]
                    if len(other_pairs) >= 2:
                        k1 = other_pairs[0]
                        k2 = other_pairs[1]
                        valid_moves.append((base + rank_map[k1][:2] + rank_map[k2][:2], "four_with_pair", r))

    return valid_moves

# --- Landlord Validator Logic End ---

def main():
    # Read Input
    try:
        line = sys.stdin.read()
        if not line: return
        full_input = json.loads(line)
    except:
        return

    # Extract Game State
    requests_hist = full_input.get("requests", [])
    responses_hist = full_input.get("responses", [])
    
    if not requests_hist: return
    
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
    
    last_move = []
    last_mover_type = "free" # or "beat"
    
    if history[1]: # Immediate previous player
        last_move = history[1]
        last_mover_type = "beat"
    elif history[0]: # Pre-previous (if immediate passed)
        last_move = history[0]
        last_mover_type = "beat"
    else:
        last_mover_type = "free"

    # Analyze Last Move
    last_type_name = "pass"
    last_len = 0
    last_rank = -1
    if last_mover_type == "beat":
        last_type_name, last_len, last_rank = check_poker_type(last_move)
    
    # Generate Valid Moves
    valid_moves_tuples = find_moves(current_hand, 
                                    target_type=last_type_name if last_mover_type == "beat" else "pass",
                                    target_len=last_len,
                                    target_rank=last_rank)
    
    response = []
    if valid_moves_tuples:
        # Pick a random move
        # heuristic: try to pick a small number of cards to play to save big ones? 
        # Or just purely random. Pure random is fine for a dummy bot.
        move = random.choice(valid_moves_tuples)
        response = move[0]
    
    print(json.dumps({
        "response": response
    }))

if __name__ == "__main__":
    main()

