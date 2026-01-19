import json
import sys
import re
import urllib.request
import urllib.error
import random

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

BOARD_SIZE = 15
COL_LABELS = "ABCDEFGHIJKLMNO"


def get_valid_moves(board):
    moves = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                moves.append((r, c))
    return moves


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

    res = "Board 15x15:\n"
    # Header
    res += "|  |"
    for char in COL_LABELS:
        res += f"{char}|"
    res += "\n"
    res += "|--|" + "-|" * BOARD_SIZE + "\n"

    for r in range(BOARD_SIZE):
        res += f"|{r+1:>2}|"  # Row number 1-15
        for c in range(BOARD_SIZE):
            val = board[r][c]
            char = symbols[val]
            res += f"{char}|"
        res += "\n"
    return res


def parse_move(content):
    # Returns 0-based (row, col)
    row, col = -1, -1

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

                if col_str in COL_LABELS:
                    col = COL_LABELS.index(col_str)
                    row = row_val - 1
                    return row, col
        except:
            continue

    # Fallback regex for col: H, row: 8
    match_explicit = re.search(r"col\D*([A-O])\D*row\D*(\d+)", content, re.IGNORECASE)
    if match_explicit:
        col_str = match_explicit.group(1).upper()
        row_val = int(match_explicit.group(2))
        col = COL_LABELS.index(col_str)
        row = row_val - 1
        return row, col

    return -1, -1


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

    # Check if I am Player 1 (Black) or Player 2 (White)
    if requests_data and requests_data[0]["x"] < 0:
        am_i_p1 = True
    else:
        am_i_p1 = False

    if am_i_p1:
        my_id = 1  # Black (X)
        opp_id = 2  # White (O)
        my_color_name = "Black (X)"
    else:
        my_id = 2  # White (O)
        opp_id = 1  # Black (X)
        my_color_name = "White (O)"

    # Fill board
    # Game sends {"x": Col, "y": Row} (0-based)
    # We store board[Row][Col]
    for r in requests_data:
        if r["x"] >= 0:
            board[r["y"]][r["x"]] = opp_id

    for r in responses_data:
        if r["x"] >= 0:
            board[r["y"]][r["x"]] = my_id

    # 3. Prepare LLM Prompt
    valid_moves = set(get_valid_moves(board))

    # Heuristic removed

    board_str = draw_board(board, my_id)
    occupied_list_str = get_occupied_list(board)

    system_prompt = """
        You are a Gomoku (Five-in-a-Row) game player.
        Gomoku is 15x15 board game. Columns are labeled A-O. Rows are labeled 1-15.
        The goal of Gomoku is to connect 5 stones in any row, column or diagonal lines to win. Opponents may block your attempts by intercepting your lines. 
        The general strategies of gomoku are:
        1. **Board Survey:** Identify 'Hot Zones' where stones are clustered. Where is the momentum?
        2. **Threat Assessment:** Does the opponent have any immediate lethal threats (4-in-a-row or open-3) in any rows, columns, or diagonal lines?
        3. **Winning Moves:** Can you create a 4-in-a-row or open-3 in any row/col/diag?
        4. **Winning:** If you have any locations to immediately form a 5-in-a-row, you should play that positon to win.
        Prepare a valid JSON object like {"col": "H", "row": 8} for your answer, along with your explanation and reason.
        Now is your turn, to your best ability, choose your move to maximize your chances of winning.
        Please briefly evaluate a few proimsing moves, provide reason for your final choice, and output the action with specified format.
        Your response format should be:
        Evaluation: [Your Evaluation]
        Reason: [Your Reason]
        Answer: [Your Answer in JSON]
    """

    state_prompt = (
        f"You are playing as {my_color_name}. It is your turn to move."
        f"{board_str}\n"
        f"**Occupied Coordinates:** {occupied_list_str}\n\n"
        "Analyze the board above.\n"
        "Find a winning move that is legally valid (Is it in the 'Occupied' list?).\n"
        "Remember to provide Explanation, Reason, and Answer."
    )

    # 4. Agentic Loop
    max_retries = 3
    final_row, final_col = -1, -1
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

        row, col = parse_move(content)

        if (row, col) in valid_moves:
            final_row, final_col = row, col
            break
        else:
            # Illegal move logic
            error_msg = ""
            if row == -1:
                error_prompt = 'Invalid format. Please output strictly JSON: {"col": "Letter", "row": Number}'
            elif not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
                error_prompt = f"Move is out of bounds."
            else:
                col_char = COL_LABELS[col]
                error_prompt = f"Move {col_char}{row+1} is invalid (occupied). Please choose an empty '.' cell."

    # 5. Fallback
    if final_row == -1:
        # Invalid value to crash out
        final_row, final_col = 98, 98
    # 6. Output
    # Output to Game: x=Col, y=Row
    resp_x, resp_y = -1, -1
    if final_row >= 0:
        resp_x = final_col
        resp_y = final_row

    print(
        json.dumps(
            {
                "response": {"x": resp_x, "y": resp_y},
                "debug": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "reasoning": reasoning_text,
                    "output": content,
                },
            }
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    main()
