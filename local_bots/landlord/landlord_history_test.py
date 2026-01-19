import json
import collections

# --- Copy of helper functions from landlord_llm.py ---
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

# --- New History Feature ---

def reconstruct_game_history(requests_hist, responses_hist):
    """
    Reconstructs the game history from Botzone requests/responses lists.
    Returns:
        history_log (list of str): Narrative log lines.
        seen_cards (Counter): Count of every card ID seen played.
    """
    history_log = []
    seen_cards = collections.Counter()
    
    # We iterate through the history.
    # The number of full rounds completed is len(responses_hist).
    # requests_hist[i] corresponds to the state BEFORE we made responses_hist[i].
    # requests_hist[i]["history"] contains the moves of the other 2 players 
    # that happened between responses_hist[i-1] (or start) and now.
    
    for i in range(len(responses_hist) + 1):
        # We can go up to len(responses_hist) to get the "current" partial round context 
        # from requests_hist[-1] if needed, but usually we just want past history.
        # Let's align with the loop: i=0 is round 1 (or 0-indexed).
        
        if i >= len(requests_hist): break
        
        # Get opponents' moves relative to this turn
        # history is [RightPlayerMove, LeftPlayerMove] (Next, Prev) based on our analysis
        opponents_moves = requests_hist[i].get("history", [[], []])
        
        # Determine "Round" number roughly.
        round_num = i + 1
        
        # Next Player (Right)
        next_move = opponents_moves[0]
        if next_move:
            history_log.append(f"Turn {round_num} (Next Player): {format_cards(next_move)}")
            for c in next_move: seen_cards[c] += 1
        elif i > 0: # Don't log "Pass" for the pre-game state
             history_log.append(f"Turn {round_num} (Next Player): Pass")

        # Prev Player (Left)
        prev_move = opponents_moves[1]
        if prev_move:
            history_log.append(f"Turn {round_num} (Prev Player): {format_cards(prev_move)}")
            for c in prev_move: seen_cards[c] += 1
        elif i > 0:
             history_log.append(f"Turn {round_num} (Prev Player): Pass")
             
        # My Move (if we have made one for this index)
        if i < len(responses_hist):
            my_move = responses_hist[i]
            if my_move:
                history_log.append(f"Turn {round_num} (You): {format_cards(my_move)}")
                for c in my_move: seen_cards[c] += 1
            else:
                history_log.append(f"Turn {round_num} (You): Pass")
                
    return history_log, seen_cards

def calculate_unknown_cards(my_hand, seen_cards):
    """
    Calculates cards that are neither in my hand nor seen played.
    Returns:
        unknown_list_str (str): Formatted list of unknown cards.
    """
    # Total deck: 0-53
    total_deck = list(range(54))
    
    # My hand set
    my_hand_set = set(my_hand)
    
    unknown_ids = []
    
    for c in total_deck:
        if c in my_hand_set: continue
        if seen_cards[c] > 0: continue # It was played
        unknown_ids.append(c)
        
    # Group by rank for display (e.g. "A: 2, K: 1")
    rank_counts = collections.defaultdict(int)
    for c in unknown_ids:
        rank_counts[get_card_rank(c)] += 1
        
    # Format
    output_parts = []
    # Iterate high to low
    for r in range(14, -1, -1): # 14(RedJoker) to 0(3)
        count = rank_counts[r]
        if count > 0:
            rank_str = ""
            if r == 14: rank_str = "RedJoker"
            elif r == 13: rank_str = "BlackJoker"
            else: rank_str = RANKS[r]
            
            output_parts.append(f"{rank_str}: {count}")
            
    return ", ".join(output_parts)

def main():
    # Test Data (extracted from a sample run or constructed)
    print("Testing Game History Reconstruction...")
    
    # Mock Input Scenario:
    # Round 1: Me (P0) plays 555 (IDs 8,9,10). Next(P1) plays 333 (IDs 0,1,2). Prev(P2) Pass.
    # Round 2: Me (P0) Pass. Next(P1) plays 7 (ID 16). Prev(P2) plays 8 (ID 20).
    # Round 3: Me (P0) plays 9 (ID 24). Next(P1) Pass. Prev(P2) plays K (ID 40).
    
    mock_requests = [
        {"history": [[], []], "own": [0,1,2,3,4,5]}, # Start (My Turn 1)
        {"history": [[0,1,2], []], "own": [0,1,2,3,4,5]}, # Turn 2 request (contains Turn 1 opponent moves: P1=333, P2=Pass)
        {"history": [[16], [20]], "own": [0,1,2,3,4,5]}, # Turn 3 request (contains Turn 2 opponent moves: P1=7, P2=8)
        {"history": [[], [40]], "own": [0,1,2,3,4,5]}, # Turn 4 request (contains Turn 3 opponent moves: P1=Pass, P2=K)
    ]
    
    # Responses we made
    mock_responses = [
        [8,9,10], # Turn 1: I play 555
        [],       # Turn 2: I Pass
        [24],     # Turn 3: I play 9
    ]
    
    # Run reconstruction
    log, seen = reconstruct_game_history(mock_requests, mock_responses)
    
    # Simulate Prompt Construction
    history_log_str = "\n".join(log)
    unknown_str = calculate_unknown_cards([4,5], seen)
    
    print("\n=== SIMULATED LLM PROMPT CONTEXT ===")
    print(f"--- Game History (Recent) ---\n{history_log_str}\n")
    print(f"--- Cards Remaining Unknown (Card Counting) ---\n(Format: Rank: Count)\n{unknown_str}\n")

if __name__ == "__main__":
    main()
