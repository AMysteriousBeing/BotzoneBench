import collections
import itertools
import argparse

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
                        # Fix: Compare Main Rank (Start or End depending on definition)
                        # Standard is Main Rank is the START of sequence for comparison usually, or END?
                        # Env says: "points[0] - points[-1] == l - 1" -> Points are reverse sorted?
                        # Env check_poker_type returns "main" as pattern[0][0].
                        # For straight: "cnt == [1,1,1,1,1]" -> pattern is sorted by count (1), then rank.
                        # So main could be the highest rank?
                        # Let's check check_poker_type logic:
                        # "points = sorted(d.keys(), reverse=True)"
                        # "main = pattern[0][0]" where pattern is sorted by (count, rank).
                        # Since counts are all 1, it sorts by rank DESC.
                        # So main is the HIGHEST rank in the sequence.
                        
                        # So if target_rank is the HIGHEST rank of the previous sequence:
                        # We need window[-1] (our highest) > target_rank.
                        # window is from unique_ranks which is SORTED ASC (low to high).
                        # So window[-1] is the highest card in our candidate sequence.
                        
                        if target_type == "straight" and window[-1] <= target_rank: continue
                        
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
            min_seq_len = 2
            check_seq_lens = []
            if target_type == "airplane":
                check_seq_lens = [target_len // 3]
            elif not target_type or target_type == "pass":
                check_seq_lens = range(min_seq_len, 13)
            
            for seq_len in check_seq_lens:
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

def run_example(test_case):
    # Constructing a comprehensive "Strong Hand" for testing all types
    p0_hand = []
    
    # 1. Singles: 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A, 2, BlackJoker, RedJoker
    # 3-10: Indices 0, 4, 8, 12, 16, 20, 24, 28 (Rank 0-7)
    p0_hand.extend([0, 4, 8, 12, 16, 20, 24, 28]) 
    # J, Q, K, A: Indices 32, 36, 40, 44 (Rank 8-11)
    p0_hand.extend([32, 36, 40, 44])
    # 2: Index 48 (Rank 12)
    p0_hand.extend([48])
    # Jokers
    p0_hand.extend([52, 53])

    # 2. Pairs: Need pairs for all ranks 3-A + 2 to beat pairs/seq_pairs
    # Adding +1 to existing indices to make pairs
    for base in [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48]:
        p0_hand.append(base + 1)

    # 3. Triples: Need triples for 3-A + 2
    # Adding +2 to make triples
    for base in [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48]:
        p0_hand.append(base + 2)

    # 4. Quads (Bombs): Need quads for 3-A + 2
    # Adding +3 to make quads
    for base in [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48]:
        p0_hand.append(base + 3)
    
    # Effectively we have a Full Deck minus nothing? 
    # Wait, the prompt asked for "smaller hand but concentrated on big cards"
    # But to test BEATING every type (including low ones like single 3), we need higher cards.
    # To beat "Quad+Pairs (3333+4455)", we need higher quads.
    # Let's reduce low cards that aren't needed for specific high-value tests.
    
    # Revised Small Strong Hand:
    # High Cards: K, A, 2, Jokers (for beating high singles/pairs/triples)
    # Mid Cards: 7, 8, 9, 10, J, Q (for sequences)
    # Low Cards: 3, 4, 5 (just enough to form a bomb or two for mechanics)
    
    p0_hand = []
    # Bomb of 3s (to beat nothing but be beaten) -> Actually we want to BEAT things.
    # We need Bombs > 3333. Let's give 6666, KKKK, 2222.
    
    # Sequence 7-8-9-10-J-Q-K-A
    # Pairs 77-88-99-1010-JJ-QQ-KK-AA
    # Triples 777-888...
    
    # Constructing specifically:
    # 6666 (Bomb)
    p0_hand.extend([12, 13, 14, 15])
    # 9999 (Bomb)
    p0_hand.extend([24, 25, 26, 27])
    # KKKK (Bomb)
    p0_hand.extend([40, 41, 42, 43])
    # 2222 (Bomb)
    p0_hand.extend([48, 49, 50, 51])
    # Jokers
    p0_hand.extend([52, 53])
    
    # Sequence coverage: 7, 8, 9, 10, J, Q, K, A
    # We already have 9s and Ks. Add 7, 8, 10, J, Q, A.
    # Let's make them Triples to cover Triple/Plane/SeqPair beats.
    # 777
    p0_hand.extend([16, 17, 18])
    # 888
    p0_hand.extend([20, 21, 22])
    # 10 10 10
    p0_hand.extend([28, 29, 30])
    # J J J
    p0_hand.extend([32, 33, 34])
    # Q Q Q
    p0_hand.extend([36, 37, 38])
    # A A A
    p0_hand.extend([44, 45, 46])
    
    # Singles/Pairs are covered by subsets of Triples/Quads.
    
    p0_hand.sort()

    scenarios = [
        ([0], "Single (3)"),
        ([0, 1], "Pair (33)"),
        ([0, 1, 2], "Triplet (333)"),
        ([0, 1, 2, 4], "Triplet+Single (3334)"),
        ([0, 1, 2, 4, 5], "Triplet+Pair (33344)"),
        ([0, 4, 8, 12, 16], "Sequence (34567)"),
        ([0, 1, 4, 5, 8, 9], "Seq Pairs (334455)"),
        ([0, 1, 2, 4, 5, 6], "Seq Triples (333444)"),
        ([0, 1, 2, 3], "Bomb (3333)"),
        ([0, 1, 2, 3, 4, 8], "Quad+Singles (3333+45)"),
        ([0, 1, 2, 3, 4, 5, 8, 9], "Quad+Pairs (3333+4455)")
    ]

    if test_case == "beat" or test_case == "all":
        print(f"--- Testing Counter-Moves with Strong Hand ---")
        print(f"Hand: {format_cards(p0_hand)}")
        
        for cards, desc in scenarios:
            last_type, last_len, last_rank = check_poker_type(cards)
            print(f"\n[Test] Beat {desc} -> {format_cards(cards)}")
            print(f"       Type: {last_type}, Rank: {last_rank}")
            
            moves = find_moves(p0_hand, last_type, last_len, last_rank)
            moves.sort(key=lambda x: (x[2], x[0]))
            
            if moves:
                print(f"       Found {len(moves)} moves.")
                for m in moves: # Print ALL moves
                    print(f"         {m[1]}: {format_cards(m[0])}")
            else:
                print("       No valid moves found (Unexpected for Strong Hand!)")

    if test_case == "free" or test_case == "all":
        print("\n--- Testing Free Play (No Previous Move) ---")
        # Long sequence of pairs test case
        # 66 77 88 99 1010 JJ QQ
        small_hand = [12, 13, 16, 17, 20, 21, 24, 25, 28, 29, 32, 33, 36, 37] 
        print(f"Hand: {format_cards(small_hand)}")
        
        print("\nValid Free Moves:")
        free_moves = find_moves(small_hand, target_type="pass") 
        free_moves.sort(key=lambda x: (x[1], x[2]))
        
        for m in free_moves:
            print(f"  {m[1]} ({m[2]}): {format_cards(m[0])}")

def main():
    parser = argparse.ArgumentParser(description="Test Landlord Validator Logic")
    parser.add_argument("test", nargs="?", choices=["beat", "free", "all"], default="all", 
                        help="Choose test case: 'beat' (counter-play), 'free' (free play), or 'all'")
    args = parser.parse_args()
    
    run_example(args.test)

if __name__ == "__main__":
    main()
