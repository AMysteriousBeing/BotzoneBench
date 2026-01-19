"""
黑白棋(Reversi) LLM样例程序
游戏信息: http://www.botzone.org/games#Reversi
"""

import json
import numpy
import random
import re
import copy

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)


DIR = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))  # 方向向量
vertical_markers = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
    4: "E",
    5: "F",
    6: "G",
    7: "H",
}

vertical_marker_to_location = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6,
    "H": 7,
}


# 放置棋子，计算新局面
def place(board, x, y, color):
    if x < 0:
        return False
    board[x][y] = color
    valid = False
    for d in range(8):
        i = x + DIR[d][0]
        j = y + DIR[d][1]
        while 0 <= i and i < 8 and 0 <= j and j < 8 and board[i][j] == -color:
            i += DIR[d][0]
            j += DIR[d][1]
        if 0 <= i and i < 8 and 0 <= j and j < 8 and board[i][j] == color:
            while True:
                i -= DIR[d][0]
                j -= DIR[d][1]
                if i == x and j == y:
                    break
                valid = True
                board[i][j] = color
    return valid


# 随机产生决策
def randplace(board, color):
    x = y = -1
    moves = []
    for i in range(8):
        for j in range(8):
            if board[i][j] == 0:
                newBoard = board.copy()
                if place(newBoard, i, j, color):
                    moves.append((i, j))
    if len(moves) == 0:
        return -1, -1
    return random.choice(moves)


# 处理输入，还原棋盘
def initBoard():
    fullInput = json.loads(input())
    requests = fullInput["requests"]
    responses = fullInput["responses"]
    board = numpy.zeros((8, 8), dtype=numpy.int32)
    board[3][4] = board[4][3] = 1
    board[3][3] = board[4][4] = -1
    myColor = 1
    if requests[0]["x"] >= 0:
        myColor = -1
        place(board, requests[0]["x"], requests[0]["y"], -myColor)
    turn = len(responses)
    for i in range(turn):
        place(board, responses[i]["x"], responses[i]["y"], myColor)
        place(board, requests[i + 1]["x"], requests[i + 1]["y"], -myColor)
    return board, myColor


def find_valid_moves(board, color):
    moves = []
    for i in range(8):
        for j in range(8):
            if board[i][j] == 0:
                newBoard = board.copy()
                if place(newBoard, i, j, color):
                    moves.append((i, j))
    if len(moves) == 0:
        moves.append((-1, -1))
    return moves


def convert_valid_moves_for_llm(move):
    vertical = vertical_markers[move[0]]
    horizontal = move[1] + 1
    return f"({vertical}, {horizontal})"


def draw(white_locations, black_locations):
    board = "This is your game state：\n|   | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |\n|---|---|---|---|---|---|---|---|---|\n"
    for h in range(8):
        board += "| " + vertical_markers[h] + " |"
        for w in range(8):
            if (h, w) in white_locations:
                board += " * |"
            elif (h, w) in black_locations:
                board += " @ |"
            else:
                board += " . |"
        board += "\n"
    return board


def init_locations():
    white_locations = [(3, 3), (4, 4)]
    black_locations = [(3, 4), (4, 3)]
    return white_locations, black_locations


def convert_text_output_to_location(vertical_marker, horizontal_marker):
    return (vertical_marker_to_location[vertical_marker], int(horizontal_marker) - 1)


def read_in_board_info(board):
    """
    Docstring for read_in_board_info

    :param board: list of list, 0: empty, -1: black, 1: white
    return: white_locations, black_locations
    """
    white_location_list = []
    black_location_list = []
    for h in range(8):
        for w in range(8):
            if board[h][w] == 1:
                white_location_list.append((h, w))
            elif board[h][w] == -1:
                black_location_list.append((h, w))
    return white_location_list, black_location_list


def generate_prompt_from_color(myColor):
    if myColor == 1:
        # black
        return "Your piece will be marked with '*', oppoent's with '@', and empty space with '.'.\n"
    elif myColor == -1:
        return "Your piece will be marked with '@', oppoent's with '*', and empty space with '.'.\n"


def extract_move(answer_str):
    if re.search(r"\b(none|None|NONE)\b", answer_str):
        return (-1, -1)
    # 匹配A-H之间的字母和1-8之间的数字
    pattern = r"([A-Ha-h])\s*[,，]?\s*(\d)"
    match = re.search(pattern, answer_str)

    if match:
        letter = match.group(1).upper()  # 转换为大写
        number = match.group(2)
        return letter, number
    return (-1, -1)


rule_prompt = """
Reversi (also known as Othello) is a two-player board game where players take turns placing pieces on an 8x8 board.
On each turn, a player may place a piece only in a position that meets both of the following conditions:

1. The position is empty.

2. From that position, in at least one of the eight directions (horizontal, vertical, or diagonal), there is a piece of the player’s own color such that all positions between it and the new piece are occupied solely by the opponent’s pieces, with no empty spaces in between.

After placing the piece, the player must flip all of the opponent's pieces that are sandwiched between their new piece and any of their existing pieces in any direction.
If a player has no valid move available, their turn is skipped.
The game ends when both players have no valid moves. The player with the greater number of pieces on the board wins.

The board is represented using coordinates A-H for columns and 1-8 for rows.
You are a Reversi player, and it is currently your turn.
Choose your move to maximize your chances of winning.
"""

final_prompt = """
Now is your turn, to your best ability, please briefly evaluate a few proimsing moves, provide reason for your final choice, and output the action with specified format.
    Your response format should be:
    Evaluation: [Your Evaluation]
    Reason: [Your Reason]
    Answer: [Your Answer]
Output valid action if possible, the coordinate should be in the form of (A-H,1-8).
If there is no valid action, output 'None'
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


def state_info_and_prompts():
    board, myColor = initBoard()
    # print(board, myColor)
    # x, y = randplace(board, myColor)

    # 获得白棋，黑棋位置
    white_list, black_list = read_in_board_info(board)
    # 计算合法位置
    valid_moves = find_valid_moves(board, myColor)
    # 转换成符合LLM输入的合法位置
    valid_llm_moves = []
    if valid_moves[0] != (-1, -1):
        for move in valid_moves:
            llm_move = convert_valid_moves_for_llm(move)
            valid_llm_moves.append(llm_move)
    else:
        valid_llm_moves.append("None")
    valid_llm_move_prompt = "Your valid actions are" + ",".join(valid_llm_moves) + "\n"
    # 告诉LLM它的棋子的样子
    personal_prompt = generate_prompt_from_color(myColor)
    # 告诉LLM棋盘现在的信息
    board_for_llm = draw(white_list, black_list)
    return valid_llm_move_prompt, personal_prompt, board_for_llm, valid_moves


if __name__ == "__main__":
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
        print(
            json.dumps(
                {"response": {"x": -1, "y": -1}, "debug": "Invalid access mode."}
            )
        )
    if access_mode:
        valid_llm_move_prompt, personal_prompt, board_for_llm, valid_moves = (
            state_info_and_prompts()
        )
        trial_count = 0
        # directly output result if no valid moves
        if "None" in valid_llm_move_prompt:
            print(json.dumps({"response": {"x": -1, "y": -1}}))
            trial_count = 3
        previous_answers = []
        x = -1
        y = -1
        while trial_count < 3:
            trial_count += 1
            if len(previous_answers) == 0:
                prev_response_prompt = ""
            else:
                prev_response_prompt = (
                    "Your previous invalid outputs: "
                    + ", ".join(previous_answers)
                    + ".\n"
                )

            # construct system prompt and user prompt
            system_prompt = rule_prompt + final_prompt
            user_prompt = (
                personal_prompt
                + board_for_llm
                + valid_llm_move_prompt
                + prev_response_prompt
            )

            # gether response from llm
            responsed_text, reasoning_text = query_api(
                api_base,
                api_key,
                model_name,
                system_prompt,
                user_prompt,
            )
            extracted_answer = extract_answer(responsed_text)
            letter, number = extract_move(extracted_answer)
            if letter != -1:
                x, y = convert_text_output_to_location(letter, number)

                if (x, y) in valid_moves:
                    break
                else:
                    previous_answers.append(f"({letter},{number})")
            else:
                previous_answers.append(f"(No Valid Move)")
                x = -1
                y = -1
        if "None" not in valid_llm_move_prompt:
            print(
                json.dumps(
                    {
                        "response": {"x": x, "y": y},
                        "debug": {
                            "system_prompt": system_prompt,
                            "user_prompt": user_prompt,
                            "reasoning": reasoning_text,
                            "output": responsed_text,
                        },
                    }
                )
            )
