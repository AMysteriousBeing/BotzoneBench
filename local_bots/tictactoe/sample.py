
import json
import sys
import random

def main():
    try:
        line = sys.stdin.read()
        if not line: return
        full_input = json.loads(line)
    except:
        return

    requests = full_input.get("requests", [])
    responses = full_input.get("responses", [])
    
    # Reconstruct Board
    board = [[0]*3 for _ in range(3)]
    
    curr = 1 # X
    for i in range(len(requests)):
        r = requests[i]
        if r["x"] >= 0:
            board[r["x"]][r["y"]] = curr
            curr *= -1
        
        if i < len(responses):
            resp = responses[i]
            if resp["x"] >= 0:
                board[resp["x"]][resp["y"]] = curr
                curr *= -1
                
    valid_moves = []
    for r in range(3):
        for c in range(3):
            if board[r][c] == 0:
                valid_moves.append((r, c))
                
    x, y = -1, -1
    if valid_moves:
        move = random.choice(valid_moves)
        x, y = move[0], move[1]
        
    print(json.dumps({
        "response": {"x": x, "y": y},
        "debug": f"SimpleBot chose {x},{y}"
    }))

if __name__ == "__main__":
    main()
