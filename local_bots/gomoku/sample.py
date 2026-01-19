
import json
import sys
import random

# Simple Random Gomoku Bot

BOARD_SIZE = 15

def main():
    try:
        line = sys.stdin.read()
        if not line: return
        full_input = json.loads(line)
    except:
        return

    requests = full_input["requests"]
    responses = full_input["responses"]
    
    # Reconstruct Board to find valid moves
    board = [[0]*BOARD_SIZE for _ in range(BOARD_SIZE)]
    
    # Check if I am Player 1 or 2
    # If requests[0].x < 0, I am P1.
    my_id = 1
    opp_id = 2
    if requests[0]["x"] >= 0:
        # If first request is a move, I am P2
        pass 
    
    # Fill board
    for r in requests:
        if r["x"] >= 0:
            board[r["x"]][r["y"]] = opp_id
            
    for r in responses:
        if r["x"] >= 0:
            board[r["x"]][r["y"]] = my_id
            
    # Valid moves
    valid_moves = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                valid_moves.append((r, c))
                
    if valid_moves:
        # Heuristic: Pick a move near center or random
        # Just random for now
        move = random.choice(valid_moves)
        print(json.dumps({"response": {"x": move[0], "y": move[1]}}))
    else:
        # Board full?
        pass

if __name__ == "__main__":
    main()
