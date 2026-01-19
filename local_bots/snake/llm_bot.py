
import json
import sys
from openai import OpenAI

# Initialize OpenAI Client
client = OpenAI(
    base_url="http://172.17.0.1:11434/v1",
    api_key="dummy"
)

# Directions: 0=Up, 1=Right, 2=Down, 3=Left (Standard Botzone)
# x is row (height), y is col (width)
dx = [-1, 0, 1, 0]
dy = [0, 1, 0, -1]

def get_valid_moves(board, head, H, W):
    moves = []
    x, y = head
    for d in range(4):
        nx, ny = x + dx[d], y + dy[d]
        # Check bounds (1-based indexing typically used in Botzone obstacle list, but let's check init)
        # Usually Botzone coords are 1-based.
        if 1 <= nx <= H and 1 <= ny <= W:
            if board[nx][ny] == 0: # 0 is empty
                moves.append(d)
    return moves

def draw_board(board, H, W, my_head, opp_head):
    # Symbols: 
    # 0=Empty, -1=Obstacle
    # 1=Me, 2=Opponent (Body)
    # H=MyHead, E=EnemyHead
    
    symbols = {0: '.', -1: '#', 1: 'o', 2: 'x'}
    res = f"Board Size: {H}x{W}\n"
    
    for r in range(1, H + 1):
        for c in range(1, W + 1):
            val = board[r][c]
            if (r, c) == my_head:
                res += "H "
            elif (r, c) == opp_head:
                res += "E "
            else:
                res += f"{symbols.get(val, '?')} "
        res += "\n"
    return res

def main():
    # 1. Read Input
    try:
        line = sys.stdin.read()
        if not line: return
        full_input = json.loads(line)
    except:
        return

    requests = full_input["requests"]
    responses = full_input["responses"]
    
    # 2. Parse Init Data (Round 0)
    init_req = requests[0]
    W = init_req["width"]
    H = init_req["height"]
    obstacles = init_req["obstacle"] # list of {x, y}
    
    # My Start Pos
    my_start = (init_req["x"], init_req["y"])
    
    # Calculate Opponent Start Pos (Symmetric usually)
    # Botzone Snake usually spawns symmetric: (H+1-x, W+1-y)
    # But we don't receive it explicitly in request[0].
    # However, we are Player 1 (if len(responses)==len(requests)-1) or Player 2.
    # Actually, Botzone 'requests' for Turn 0 contains MY starting pos.
    # Opponent pos is inferred or we wait for their move?
    # In Snake, we assume we know where they start.
    opp_start = (H + 1 - my_start[0], W + 1 - my_start[1])

    # 3. Reconstruct State
    # Board: 1-based indexing [1..H][1..W]
    board = [[0] * (W + 2) for _ in range(H + 2)]
    
    # Mark Obstacles
    for obs in obstacles:
        board[obs['x']][obs['y']] = -1
        
    # Snakes
    my_body = [my_start]
    opp_body = [opp_start]
    
    # Mark Initial Bodies on Board
    board[my_start[0]][my_start[1]] = 1
    board[opp_start[0]][opp_start[1]] = 2

    # Replay Moves
    # requests[1] is Opponent's move in Turn 0 (Round 0)
    # responses[0] is My move in Turn 0
    
    turn_count = len(responses) # Current turn index to decide
    
    # Simulate history
    # Round 0, 1, 2...
    # Note: requests[i+1] corresponds to opponent move in round i
    # responses[i] corresponds to my move in round i
    
    current_round = 0
    
    # History length
    history_len = len(requests) - 1 
    # if I am to move, I have 'history_len' opponent moves, and 'history_len' my moves (from prev rounds)
    # Wait, if it's my turn, I have made 'turn_count' responses.
    # Opponent has made 'len(requests)-1' moves.
    
    for i in range(turn_count):
        # Get moves
        my_dir = responses[i]["direction"]
        opp_dir = requests[i+1]["direction"]
        
        # Grow rule: Rounds 0-9 grow; Round >9, grow if round % 3 == 0
        grow = (current_round < 10) or (current_round % 3 == 0)
        
        # Move Me
        mx, my = my_body[-1]
        nmx, nmy = mx + dx[my_dir], my + dy[my_dir]
        my_body.append((nmx, nmy))
        board[nmx][nmy] = 1 # head
        
        # Move Opponent
        ox, oy = opp_body[-1]
        nox, noy = ox + dx[opp_dir], oy + dy[opp_dir]
        opp_body.append((nox, noy))
        board[nox][noy] = 2 # head
        
        if not grow:
            # Remove tails
            tmx, tmy = my_body.pop(0)
            board[tmx][tmy] = 0
            tox, toy = opp_body.pop(0)
            board[tox][toy] = 0
            
            # Re-mark bodies (in case of overlap/head collision handling, but simplified here)
            for bx, by in my_body: board[bx][by] = 1
            for bx, by in opp_body: board[bx][by] = 2
            
        current_round += 1

    # Current State
    my_head = my_body[-1]
    opp_head = opp_body[-1]
    
    # 4. Prepare LLM Prompt
    valid_moves = get_valid_moves(board, my_head, H, W)
    # Convert valid moves to text (Up/Right/Down/Left)
    dir_names = ["Up", "Right", "Down", "Left"]
    valid_move_names = [dir_names[d] for d in valid_moves]
    
    board_str = draw_board(board, H, W, my_head, opp_head)
    
    system_prompt = (
        "You are a Snake Game expert. "
        "You control the snake marked 'H' (Head) and 'o' (Body). "
        "The opponent is 'E' (Head) and 'x' (Body). "
        "Obstacles are '#'. Empty space is '.'. "
        "Your goal is to survive and trap the opponent. "
        "Do NOT hit walls, obstacles, or snakes."
    )
    
    user_prompt = (
        f"{board_str}\n"
        f"Valid moves: {valid_move_names}\n"
        "Output ONLY a JSON object with the best move direction: {\"direction\": \"Up\"}"
    )

    import os
    debug_log = ""
    
    # 5. Call LLM
    try:
        # Log prompt to file
        log_entry = (f"-" * 20 + "\n" +
                     f"System: {system_prompt}\n" +
                     f"User: {user_prompt}\n")

        try:
            log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_log.txt")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

        debug_log = log_entry

        response = client.chat.completions.create(
            model="qwen3:4b-15360",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content
    except Exception as e:
        # Fallback random
        content = ""

    # 6. Parse Output
    chosen_dir = -1
    
    # Map back to ints
    name_to_int = {"UP": 0, "RIGHT": 1, "DOWN": 2, "LEFT": 3}
    
    import re
    match = re.search(r'\"direction\":\s*\"(\w+)\"', content, re.IGNORECASE)
    if match:
        d_str = match.group(1).upper()
        if d_str in name_to_int:
            chosen_dir = name_to_int[d_str]

    # Validate
    if chosen_dir not in valid_moves:
        if valid_moves:
            chosen_dir = valid_moves[0] # Fallback
        else:
            chosen_dir = 0 # Suicide (no moves)

    # 7. Output
    print(json.dumps({
        "response": {"direction": chosen_dir},
        "debug": debug_log
    }))

if __name__ == "__main__":
    main()

