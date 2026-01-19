
import json
import sys
import random

# Simple Random Go Bot

BOARD_SIZE = 9

def main():
    try:
        line = sys.stdin.read()
        if not line: return
        full_input = json.loads(line)
    except Exception as e:
        sys.stderr.write(f"JSON Parse Error: {e}\n")
        return

    requests = full_input["requests"]
    responses = full_input["responses"]
    
    # Reconstruct Board to find valid moves
    board = [[0]*BOARD_SIZE for _ in range(BOARD_SIZE)]
    
    # Check if I am Player 1 or 2
    my_id = 1
    opp_id = 2
    
    # Requests[0] is usually init
    if requests and requests[0]["x"] == -2:
        # I am P1
        pass
    else:
        # I am P2
        pass
        
    # Fill board (Naive)
    try:
        for r in requests:
            if r["x"] > 0 and r["y"] > 0:
                # Convert 1-based to 0-based
                # x=Col, y=Row -> board[y][x]
                board[r["y"]-1][r["x"]-1] = opp_id
                
        for r in responses:
            if r["x"] > 0 and r["y"] > 0:
                # Convert 1-based to 0-based
                board[r["y"]-1][r["x"]-1] = my_id
    except Exception as e:
        sys.stderr.write(f"Board Fill Error: {e}\n")
            
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
        # Convert 0-based to 1-based
        # move is (row, col) -> (y, x)
        # Output x (Col) = move[1]+1, y (Row) = move[0]+1
        output = json.dumps({"response": {"x": move[1]+1, "y": move[0]+1}, "debug": f"SimpleBot chose {move}"})
        print(output)
        sys.stdout.flush()
        sys.stderr.write(f"SimpleBot output: {output}\n")
    else:
        # Pass
        print(json.dumps({"response": {"x": -1, "y": -1}}))
        sys.stdout.flush()

if __name__ == "__main__":
    main()
