import json
import sys
import re
import urllib.request
import urllib.error
import random
import requests

# Configuration for Qwen 8B
API_KEY = "sk-wegasvkuoirqeeghwmnrmpzgxnstzpsqldjnzlgstgsekjjs"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen3-8B"

BOARD_SIZE = 9
COL_LABELS = "ABCDEFGHI"


def get_valid_moves(board):
    moves = []
    # We will filter these later or use is_suicide check if needed
    # But for now, basic empty check.
    # Actually, let's make this robust.
    # Note: We need my_id to check suicide.
    # This function is called before we set my_id in the original code order.
    # We will move it or update it.
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                moves.append((r, c))
    return moves


def get_liberties(board, r, c):
    # flood fill to find group and liberties
    color = board[r][c]
    if color == 0:
        return 0

    stack = [(r, c)]
    visited = {(r, c)}
    liberties = set()

    while stack:
        curr_r, curr_c = stack.pop()

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = curr_r + dr, curr_c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                if board[nr][nc] == 0:
                    liberties.add((nr, nc))
                elif board[nr][nc] == color and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    stack.append((nr, nc))

    return len(liberties)


def is_suicide(board, r, c, color):
    # 1. Place stone temporarily
    # 2. Check if it captures any opponent groups (if so, not suicide)
    # 3. If no capture, check if it has liberties

    # Copy board (shallow copy)
    temp_board = [row[:] for row in board]
    temp_board[r][c] = color

    opp_color = 3 - color
    captured = False

    # Check neighbors for opponent groups with 0 liberties
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
            if temp_board[nr][nc] == opp_color:
                if get_liberties(temp_board, nr, nc) == 0:
                    captured = True
                    break

    if captured:
        return False

    # Check if self has liberties
    if get_liberties(temp_board, r, c) == 0:
        return True

    return False


def get_forbidden_moves(board, my_id):
    suicide_moves = []

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                if is_suicide(board, r, c, my_id):
                    label = f"{COL_LABELS[c]}{r+1}"
                    suicide_moves.append(label)

    if not suicide_moves:
        return "None"
    return ", ".join(suicide_moves)


def get_occupied_list(board):
    occupied = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != 0:
                # Format: "A1", "D4"
                label = f"{COL_LABELS[c]}{r+1}"
                occupied.append(label)

    if not occupied:
        return "None (Board is empty)"
    return ", ".join(occupied)


def draw_board(board, my_symbol):
    # Symbols: 0=., 1=X, 2=O
    # 1=Black(X), 2=White(O)
    symbols = {0: ".", 1: "X", 2: "O"}

    res = "Go Board 9x9:\n"
    # Header
    res += "   | " + " | ".join(list(COL_LABELS)) + " |\n"
    res += "---|---" + "+---" * 8 + "|\n"

    for r in range(BOARD_SIZE):
        res += f"{r+1:>2} |"  # Row number (1-9)
        for c in range(BOARD_SIZE):
            val = board[r][c]  # Standard display: board[row][col]
            char = symbols[val]
            res += f" {char} |"
        res += "\n"
        if r < BOARD_SIZE - 1:
            res += "---|---" + "+---" * 8 + "|\n"
    return res


def query_qwen(messages):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "BotzoneClient/1.0",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "max_tokens": 32768,
        "temperature": 0.7,
    }
    llm_response = requests.post(API_URL, json=payload, headers=headers)
    response_json = json.loads(llm_response.text)
    # 提取答案
    responsed_text = response_json["choices"][0]["message"]["content"]
    return responsed_text

    # try:
    #     data = json.dumps(payload).encode("utf-8")
    #     req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

    #     with urllib.request.urlopen(req, timeout=30) as response:
    #         if response.status != 200:
    #             return f"Error: HTTP {response.status}"
    #         response_body = response.read().decode("utf-8")
    #         return json.loads(response_body)["choices"][0]["message"]["content"]

    # except urllib.error.HTTPError as e:
    #     error_body = e.read().decode("utf-8") if e.fp else ""
    #     return f"Error: HTTP {e.code} - {e.reason} - {error_body}"
    # except Exception as e:
    #     return f"Error: {e}"


def parse_move(content):
    # Returns 0-based (row, col)

    # Check for pass
    if "pass" in content.lower() and "col" not in content.lower():
        # If explicitly just "pass" text without JSON structure for move
        return -1, -1

    # First try to find a JSON object in the "Answer: " section if it exists
    answer_match = re.search(r"Answer:\s*(\{.*\})", content, re.DOTALL)
    potential_jsons = []
    if answer_match:
        potential_jsons.append(answer_match.group(1))

    # Also find all JSON-like strings
    matches = re.findall(r"\{.*?\}", content, re.DOTALL)
    if matches:
        potential_jsons.extend(reversed(matches))

    for json_str in potential_jsons:
        try:
            move = json.loads(json_str)
            if "col" in move and "row" in move:
                col_str = str(move["col"]).upper()
                row_val = int(move["row"])

                if col_str == "PASS" or row_val == -1:
                    return -1, -1

                if col_str in COL_LABELS:
                    c = COL_LABELS.index(col_str)
                    r = row_val - 1
                    return r, c
        except:
            continue

    # Regex fallback
    # Look for col: "C", row: 4
    match_explicit = re.search(r"col\D*([A-I])\D*row\D*(\d+)", content, re.IGNORECASE)
    if match_explicit:
        col_str = match_explicit.group(1).upper()
        row_val = int(match_explicit.group(2))
        c = COL_LABELS.index(col_str)
        r = row_val - 1
        return r, c

    return -10, -10


def main():
    # 1. Read Input
    try:
        line = sys.stdin.read()
        if not line:
            return
        full_input = json.loads(line)
    except:
        return

    requests_data = full_input.get("requests", [])
    responses_data = full_input.get("responses", [])

    # 2. Reconstruct Board
    board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    # Determine Player Color
    # Go Protocol:
    # Turn 0: Request={x:-2, y:-2} (Init).
    # If I am P1 (Black): I respond.
    # If I am P2 (White): Request={x:?, y:?} (Black's move) -> I respond.

    if requests_data and requests_data[0]["x"] == -2:
        am_i_black = True
    else:
        am_i_black = False

    my_id = 1 if am_i_black else 2
    opp_id = 2 if am_i_black else 1

    # Fill board (Naive: No capture logic, just stone placement)
    for r in requests_data:
        if r["x"] > 0 and r["y"] > 0:
            # Convert 1-based (Env) to 0-based (Internal)
            # x is Column, y is Row in Botzone Go (usually)
            # But we want board[row][col] -> board[y][x]
            board[r["y"] - 1][r["x"] - 1] = opp_id

    for r in responses_data:
        if r["x"] > 0 and r["y"] > 0:
            board[r["y"] - 1][r["x"] - 1] = my_id

    # 3. Prepare LLM Prompt
    # Update valid moves to exclude suicide
    raw_valid_moves = get_valid_moves(board)
    valid_moves = []
    for r, c in raw_valid_moves:
        if not is_suicide(board, r, c, my_id):
            valid_moves.append((r, c))

    valid_moves = set(valid_moves)

    # Heuristic removed as per instruction

    board_str = draw_board(board, my_id)
    occupied_list_str = get_occupied_list(board)
    suicide_list_str = get_forbidden_moves(board, my_id)
    my_color_name = "Black (X)" if am_i_black else "White (O)"

    system_prompt = (
        "You are a Go (Weiqi) expert playing on a 9x9 board. "
        "Columns are labeled A-I. Rows are labeled 1-9.\n"
        f"You are playing as {my_color_name}. It is your turn to move.\n\n"
        "**BOARD LEGEND**:\n"
        "- Empty intersections are marked with '.'\n"
        "- Occupied intersections are marked with 'X' and 'O'.\n\n"
        "**RULES**:\n"
        "1. **Turns**: Black makes the first move, then White and Black alternate. A move consists of placing one stone on an empty coordinate.\n"
        "2. **Golden Rule (Availability)**: You can ONLY play on coordinates marked with a dot ('.'). NEVER play on 'X' or 'O'.\n"
        "3. **Capture**: A single or group of stones is captured and removed when all adjacent coordinates (up, down, left, right) of the stone or group of stones are occupied by the enemy.\n"
        "4. **Suicide Rule**: You CANNOT play a move that results in your stone or group of stones you have being immediately captured as in rule 3, unless that move immediately captures the opponent stones. (Capture takes precedence).\n"
        "5. **Ko Rule**: No stone may be played so as to recreate a former board position immediately.\n"
        "6. **Passing**: You may pass your turn at any time. Two consecutive passes end the game.\n"
        "7. **Objective**: The player with more area (occupied + surrounded points) wins.\n\n"
        'Prepare a valid JSON object like {"col": "C", "row": 5} for your answer, along with your explanation and reason. If you pass, output: {"col": "pass", "row": 0}. \n\n'
        "Your response format should exactly be:\n"
        "Explanation: [Your Explanation]\n"
        "Reason: [Your Reason]\n"
        "Answer: [Your Answer JSON]"
    )

    user_prompt = (
        f"{board_str}\n"
        f"**Occupied Coordinates:** {occupied_list_str}\n"
        f"**Illegal Moves (Suicide/Forbidden):** {suicide_list_str}\n\n"
        "Analyze the board above.\n"
        "Find a winning move that is legally valid (Is it in the 'Occupied' list? Is it in the 'Illegal Moves' list?).\n"
        "Remember to provide Explanation, Reason, and Answer."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 4. Agentic Loop
    max_retries = 3
    final_row, final_col = -10, -10
    debug_log = [f"System: {system_prompt}", f"User: {user_prompt}"]

    for attempt in range(max_retries):
        content = query_qwen(messages)
        debug_log.append(f"Attempt {attempt+1} Response:\n{content}")

        row, col = parse_move(content)

        # Check for Pass
        if row == -1 and col == -1:
            final_row, final_col = -1, -1
            break

        # Check validity: (col, row) must be in valid_moves
        if (row, col) in valid_moves:
            final_row, final_col = row, col
            break
        else:
            # Illegal move logic
            error_msg = ""
            if row == -10:
                error_msg = 'Invalid format. Please output strictly JSON: {"col": "Letter", "row": Number}'
            elif not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
                error_msg = f"Move is out of bounds."
            else:
                col_char = COL_LABELS[col]
                error_msg = f"Move {col_char}{row+1} is invalid (occupied). Please choose an empty '.' cell."

            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": error_msg})
            debug_log.append(f"Retry Reason: {error_msg}")

    # 5. Fallback
    if final_row == -10:
        # Invalid value to crash out
        final_row, final_col = 98, 98
        debug_log.append("Fallback: Failed. Returning 99,99 to crash.")

    # 6. Output
    # We output x=col, y=row
    # We used x=Column, y=Row internally.
    # final_row is Y (0-based), final_col is X (0-based).
    # So response x = final_col + 1, response y = final_row + 1

    resp_x, resp_y = -1, -1
    if final_row >= 0 and final_col >= 0:
        resp_x = final_col + 1
        resp_y = final_row + 1

    print(
        json.dumps(
            {"response": {"x": resp_x, "y": resp_y}, "debug": "\n".join(debug_log)}
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    main()
