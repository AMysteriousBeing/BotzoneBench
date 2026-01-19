import json
import sys
import os
import urllib.request
import urllib.error
import re

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)


def get_occupied_list(board):
    occupied = []
    for c in range(3):
        for r in range(3):
            if board[c][r] != 0:
                col_label = chr(ord("A") + c)
                row_label = r + 1
                occupied.append(f"{col_label}{row_label}")
    return ", ".join(occupied) if occupied else "None (Board is empty)"


def get_valid_moves(board):
    moves = []
    for c in range(3):
        for r in range(3):
            if board[c][r] == 0:
                moves.append((c, r))
    return moves


def draw_board(board):
    symbols = {0: ".", 1: "X", -1: "O"}
    res = "Current Board:\n"
    res += "|   | A | B | C |\n"
    res += "|---|---|---|---|\n"
    for r in range(3):
        res += "| {} |".format(r + 1)
        for c in range(3):
            res += " {} |".format(symbols[board[c][r]])
        res += "\n"
    return res


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
    # 1. Read Input from Game Engine
    try:
        line = sys.stdin.read()
        if not line:
            return
        full_input = json.loads(line)
    except:
        return

    # 2. Reconstruct Board
    # Requests are moves by P1 (X), Responses by P2 (O)
    # Board: 0=Empty, 1=X, -1=O
    # board[col][row]
    board = [[0] * 3 for _ in range(3)]

    requests = full_input.get("requests", [])
    responses = full_input.get("responses", [])

    # Determine Identity and Symbols
    # If requests[0] is init (x < 0), we are Player 1.
    # In this specific game configuration:
    # Player 1 is 'O' (-1) and goes first.
    # Player 2 is 'X' (1) and goes second.

    i_am_p1 = False
    if len(requests) > 0 and requests[0]["x"] < 0:
        i_am_p1 = True

    if i_am_p1:
        my_symbol = "O"
        my_val = -1
        op_val = 1
    else:
        my_symbol = "X"
        my_val = 1
        op_val = -1

    # Apply Requests (Opponent Moves)
    for r in requests:
        if r["x"] >= 0:
            board[r["x"]][r["y"]] = op_val

    # Apply Responses (My Moves)
    for r in responses:
        if r["x"] >= 0:
            board[r["x"]][r["y"]] = my_val

    # 3. Prepare LLM Prompt
    valid_moves = get_valid_moves(board)
    valid_moves_str = ", ".join([f"{chr(ord('A') + c)}{r+1}" for c, r in valid_moves])
    board_str = draw_board(board)
    occupied_list_str = get_occupied_list(board)

    system_prompt = """
        You are a TicTacToe expert. You and your opponent are playing as 'X' or 'O', on a 3x3 board.
        Columns are labeled from A-C. Rows are labeled from 1-3.
        You want to win or draw by forming a 3-in-a-row in any rows, columns, or diagonal lines.
        Please output a valid JSON object like {"col": 'Letter', "row": Number} for your answer.
        Please briefly evaluate a few proimsing moves, provide reason for your final choice, and output the action with specified format.
        Your response format should be:
        Evaluation: [Your Evaluation]
        Reason: [Your Reason]
        Answer: [Your Answer in JSON]
    """

    state_prompt = f"""
    It's your turn to move and you are playing as {my_symbol}.
    Your board representation is : {board_str}.
    The occupied Coordinates are: {occupied_list_str}.
    The valid moves are: {valid_moves_str}.
    """
    invalid_responses = []

    max_retries = 3
    final_x, final_y = -1, -1

    for attempt in range(max_retries):
        if len(invalid_responses) == 0:
            user_prompt = state_prompt
        else:
            invalid_response_prompt = (
                "Your previous invalid actions are: "
                + ", ".join(invalid_responses)
                + "."
            )
            user_prompt += invalid_response_prompt
        content, reasoning_text = query_api(
            api_base,
            api_key,
            model_name,
            system_prompt,
            user_prompt,
        )

        # 5. Parse Output
        x, y = -1, -1

        # Try to find JSON in Answer section
        answer_match = re.search(r"Answer:\s*(\{.*\})", content, re.DOTALL)
        potential_jsons = []
        if answer_match:
            potential_jsons.append(answer_match.group(1))

        # Also find all JSON-like strings
        matches = re.findall(r"\{.*?\}", content, re.DOTALL)
        if matches:
            potential_jsons.extend(reversed(matches))

        parsed = False
        for json_str in potential_jsons:
            try:
                move = json.loads(json_str)
                # Handle {"col": "A", "row": 1} format
                if "col" in move and "row" in move:
                    col_str = str(move["col"]).upper()
                    row_val = int(move["row"])

                    if (
                        len(col_str) == 1
                        and "A" <= col_str <= "C"
                        and 1 <= row_val <= 3
                    ):
                        x = ord(col_str) - ord("A")  # x is col
                        y = row_val - 1  # y is row
                        parsed = True
                        break
            except:
                continue

        if not parsed:
            pass

        # Validate
        if (x, y) in valid_moves:
            final_x, final_y = x, y
            break
        else:
            invalid_responses.append(f"({x}, {y})")

    # 5. Fallback (Crash if failed)
    if final_x == -1:
        final_x, final_y = -1, -1

    # 6. Output Response
    print(
        json.dumps(
            {
                "response": {"x": final_x, "y": final_y},
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
