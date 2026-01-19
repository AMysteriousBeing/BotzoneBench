import json
import sys
import random
import re
import copy
import requests

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

BOARD_SIZE = 7

# 24个方向（邻居 + 跳跃）
delta = [
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
    (0, -1),
    (1, -1),
    (1, 0),
    (2, 0),
    (2, 1),
    (2, 2),
    (1, 2),
    (0, 2),
    (-1, 2),
    (-2, 2),
    (-2, 1),
    (-2, 0),
    (-2, -1),
    (-2, -2),
    (-1, -2),
    (0, -2),
    (1, -2),
    (2, -2),
    (2, -1),
]


def in_map(x, y):
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


def proc_step(board, step, color):
    x0, y0, x1, y1 = step
    if x1 == -1:
        return True
    if not in_map(x0, y0) or not in_map(x1, y1):
        return False
    if board[x0][y0] != color:
        return False
    if board[x1][y1] != 0:
        return False

    dx, dy = abs(x0 - x1), abs(y0 - y1)
    if dx == 0 and dy == 0:
        return False
    if dx > 2 or dy > 2:
        return False

    # clone / jump
    if dx <= 1 and dy <= 1:
        # clone，不动原位置
        pass
    else:
        # jump，原位置清空
        board[x0][y0] = 0

    board[x1][y1] = color

    # flip neighbors
    for i in range(8):
        nx = x1 + delta[i][0]
        ny = y1 + delta[i][1]
        if in_map(nx, ny) and board[nx][ny] == -color:
            board[nx][ny] = color
    return True


def find_valid_moves(board, color):
    moves = []
    for x0 in range(BOARD_SIZE):
        for y0 in range(BOARD_SIZE):
            if board[x0][y0] != color:
                continue
            for dx, dy in delta:
                x1, y1 = x0 + dx, y0 + dy
                if in_map(x1, y1) and board[x1][y1] == 0:
                    # 仅添加合法动作
                    temp_board = copy.deepcopy(board)
                    if proc_step(temp_board, (x0, y0, x1, y1), color):
                        moves.append((x0, y0, x1, y1))
    if not moves:
        moves.append((-1, -1, -1, -1))
    return moves


def draw(board):
    """
    内部 board[row][col] 索引与行列对应：
        row 0 -> 行号 1
        row 6 -> 行号 7
    """
    BOARD_SIZE = 7
    vertical_markers = [chr(ord("A") + i) for i in range(BOARD_SIZE)]
    s = "This is your board state representation.\n"
    s += "|   | " + " | ".join(vertical_markers) + " |\n"
    s += "|---|" + "---|" * BOARD_SIZE + "\n"
    # 每行
    for row in range(BOARD_SIZE):
        s += f"| {row+1} |"
        for col in range(BOARD_SIZE):
            if board[row][col] == 1:
                s += " @ |"
            elif board[row][col] == -1:
                s += " * |"
            else:
                s += " . |"
        s += "\n"
    return s


def convert_move_to_text(move):
    if move[0] == -1:
        return "No"
    row0, col0, row1, col1 = move
    return f"({chr(ord('A') + col0)},{row0+1}) -> ({chr(ord('A') + col1)},{row1+1})"


def extract_move(answer_str):
    if "No" in answer_str or "None" in answer_str:
        return -1, -1, -1, -1

    pattern = r"(?:\(\s*)?([A-Ga-g])\s*[,，]?\s*(\d+)(?:\s*\))?\s*->\s*(?:\(\s*)?([A-Ga-g])\s*[,，]?\s*(\d+)(?:\s*\))?"
    match = re.search(pattern, answer_str)
    if not match:
        return -1, -1, -1, -1

    col0 = ord(match.group(1).upper()) - ord("A")
    row0 = int(match.group(2)) - 1
    col1 = ord(match.group(3).upper()) - ord("A")
    row1 = int(match.group(4)) - 1

    return row0, col0, row1, col1


def generate_system_prompt(my_color):  # 动态判断bot的颜色
    player_symbol = "@" if my_color == 1 else "*"
    opponent_symbol = "*" if my_color == 1 else "@"

    prompt = f"""
    You are an Ataxx game player. 
    Ataxx is a two-player board game played on a 7x7 grid, where players take turns moving pieces.
    Each turn, a piece can either clone to an adjacent square or jump to a square two spaces away.
    After placing a piece, all adjacent opponent pieces are flipped.
    If there are no legal moves, the turn is skipped.
    Please check the current board state and provide your move legally. Unless there is truly no legal move, always choose a move.
    The board uses A-G / 1-7 coordinates (Pay attention to the Range!).
    """
    return prompt


final_prompt = """
Important instructions: Please output your answer directly in your reply without calling any tool functions.
Provide your analysis and suggested move in plain text.
Now is your turn, to your best ability, please briefly evaluate a few promising moves, provide reason for your final choice, and output the action with specified format.
Your response format should be:
Evaluation: [Your Evaluation]
Reason: [Your Reason]
Answer: [Your Answer]
Output valid action if possible, the coordinate should be in the form of (A,1) -> (B,2).
If there is no valid action, output 'None'.
"""


def extract_answer(response_text: str) -> str:
    """
    提取answer/Answer后面的所有内容

    Args:
        response_text: 响应文本

    Returns:
        answer后面的内容字符串，如果没有找到则返回空字符串
    """
    if not response_text:
        return ""

    # 清理文本
    text = response_text.strip()

    # 匹配模式：不区分大小写，匹配"answer:"后面的所有内容
    patterns = [
        # 模式1: Answer: 后面所有内容（包含空格和换行）
        r"(?:answer|Answer|ANSWER|回答|answer is|Answer is)[\s:]*([\s\S]*)",
        # 模式2: 冒号或空格后的内容
        r"[:：]\s*([^\n]*)",
        # 模式3: 最后一行的内容（如果没有明确标记）
        r"(?:\n|^)([^\n]+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:  # 确保内容不为空
                return content

    # 如果没有找到明确的answer标记，返回整个文本
    return text


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
    else:
        print(json.dumps({"response": {"x0": -1, "y0": -1, "x1": -1, "y1": -1}}))
        trial_count = 3
    board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    board[0][0] = board[6][6] = 1
    board[6][0] = board[0][6] = -1

    # 读取输入
    data = json.loads(sys.stdin.readline().strip())
    reqs = data.get("requests", [])
    responses = data.get("responses", [])

    turnID = len(responses)
    my_color = 1 if reqs[0]["x0"] < 0 else -1
    rule_prompt = generate_system_prompt(my_color)

    player_symbol = "@" if my_color == 1 else "*"
    opponent_symbol = "*" if my_color == 1 else "@"
    color_prompt = f"Your pieces are marked with '{player_symbol}', opponents' are marked with '{opponent_symbol}', and empty spaces are '.'\n"

    # 历史复盘
    for i in range(turnID):
        # 对手动作
        if i < len(reqs):
            r = reqs[i]
            proc_step(board, (r["x0"], r["y0"], r["x1"], r["y1"]), -my_color)
        # 我方动作
        if i < len(responses):
            me = responses[i]
            proc_step(board, (me["x0"], me["y0"], me["x1"], me["y1"]), my_color)

    # 当前回合对手动作
    if turnID < len(reqs):
        cur = reqs[turnID]
        proc_step(board, (cur["x0"], cur["y0"], cur["x1"], cur["y1"]), -my_color)

    # 找所有合法动作
    valid_moves = find_valid_moves(board, my_color)
    valid_moves_text = (
        [convert_move_to_text(m) for m in valid_moves]
        if valid_moves[0] != (-1, -1, -1, -1)
        else ["No"]
    )
    valid_prompt = "Your valid actions are：" + ",".join(valid_moves_text) + ".\n"

    board_for_llm = draw(board)
    previous_answers = []
    trial_count = 0
    x = y = x1 = y1 = -1

    # 如果没有合法动作，直接返回
    if "No" in valid_prompt:
        print(json.dumps({"response": {"x0": -1, "y0": -1, "x1": -1, "y1": -1}}))
        return

    while trial_count < 3:
        trial_count += 1
        prev_response_prompt = ""
        if previous_answers:
            prev_response_prompt = (
                "Your previous invalid outputs are:"
                + ",".join(previous_answers)
                + ".\n"
            )
        system_prompt = rule_prompt + final_prompt
        user_prompt = color_prompt + board_for_llm + valid_prompt + prev_response_prompt
        responsed_text = ""
        try:
            responsed_text, reasoning_text = query_api(
                api_base,
                api_key,
                model_name,
                system_prompt,
                user_prompt,
            )
        except Exception:
            pass

        # 提取动作
        extracted_answer = extract_answer(responsed_text)
        x, y, x1, y1 = extract_move(extracted_answer)
        if (x, y, x1, y1) in valid_moves:
            break
        else:
            previous_answers.append(extracted_answer)

    # fallback：随机合法动作
    # if (x, y, x1, y1) not in valid_moves:
    #    fallback = random.choice(valid_moves)
    #    x, y, x1, y1 = fallback

    print(
        json.dumps(
            {
                "response": {"x0": x, "y0": y, "x1": x1, "y1": y1},
                "debug": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "reasoning": reasoning_text,
                    "output": responsed_text,
                },
            }
        )
    )


if __name__ == "__main__":
    main()
