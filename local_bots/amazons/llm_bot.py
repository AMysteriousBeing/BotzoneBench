import sys
import json
import random
import requests
import re

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

GRIDSIZE = 8
OBSTACLE = 2
GRID_BLACK = 1
GRID_WHITE = -1

dx = [-1, -1, -1, 0, 0, 1, 1, 1]
dy = [-1, 0, 1, -1, 1, -1, 0, 1]

gridInfo = [[0] * GRIDSIZE for _ in range(GRIDSIZE)]
currBotColor = None


def in_map(x, y):
    return 0 <= x < GRIDSIZE and 0 <= y < GRIDSIZE


def ProcStep(x0, y0, x1, y1, x2, y2, color, check_only):
    if not (in_map(x0, y0) and in_map(x1, y1) and in_map(x2, y2)):
        return False

    if gridInfo[x0][y0] != color or gridInfo[x1][y1] != 0:
        return False

    if gridInfo[x2][y2] != 0 and not (x2 == x0 and y2 == y0):
        return False

    if not check_only:
        gridInfo[x0][y0] = 0
        gridInfo[x1][y1] = color
        gridInfo[x2][y2] = OBSTACLE

    return True


def init_board():
    a = (GRIDSIZE - 1) // 3
    # 黑
    gridInfo[0][a] = GRID_BLACK
    gridInfo[a][0] = GRID_BLACK
    gridInfo[GRIDSIZE - 1 - a][0] = GRID_BLACK
    gridInfo[GRIDSIZE - 1][a] = GRID_BLACK
    # 白
    gridInfo[0][GRIDSIZE - 1 - a] = GRID_WHITE
    gridInfo[a][GRIDSIZE - 1] = GRID_WHITE
    gridInfo[GRIDSIZE - 1 - a][GRIDSIZE - 1] = GRID_WHITE
    gridInfo[GRIDSIZE - 1][GRIDSIZE - 1 - a] = GRID_WHITE


# 合法动作生成
def find_all_moves(color):
    beginPos, movePos, arrowPos = [], [], []

    for i in range(GRIDSIZE):
        for j in range(GRIDSIZE):
            if gridInfo[i][j] != color:
                continue

            for k in range(8):
                for d1 in range(1, GRIDSIZE):
                    xx = i + dx[k] * d1
                    yy = j + dy[k] * d1
                    if not in_map(xx, yy) or gridInfo[xx][yy] != 0:
                        break

                    for l in range(8):
                        for d2 in range(1, GRIDSIZE):
                            xxx = xx + dx[l] * d2
                            yyy = yy + dy[l] * d2
                            if not in_map(xxx, yyy):
                                break
                            if gridInfo[xxx][yyy] != 0 and not (xxx == i and yyy == j):
                                break

                            if ProcStep(i, j, xx, yy, xxx, yyy, color, True):
                                beginPos.append((i, j))
                                movePos.append((xx, yy))
                                arrowPos.append((xxx, yyy))
    return beginPos, movePos, arrowPos


def board_to_ascii():
    LETTER = "ABCDEFGH"
    s = ""

    # 顶部列号
    s += "|   | " + " | ".join(str(i + 1) for i in range(GRIDSIZE)) + " |\n"
    s += "|---|" + "---|" * GRIDSIZE + "\n"

    # 每一行
    for i in range(GRIDSIZE):
        s += f"| {LETTER[i]} |"
        for j in range(GRIDSIZE):
            v = gridInfo[i][j]
            if v == GRID_BLACK:
                s += " B |"
            elif v == GRID_WHITE:
                s += " W |"
            elif v == OBSTACLE:
                s += " X |"
            else:
                s += " . |"
        s += "\n"

    return s


def moves_to_text(beginPos, movePos, arrowPos):
    lines = []
    for i in range(len(beginPos)):
        x0, y0 = beginPos[i]
        x1, y1 = movePos[i]
        x2, y2 = arrowPos[i]
        lines.append(f"({x0},{y0})->({x1},{y1})->({x2},{y2})")
    return "\n".join(lines)


def build_system_prompt():
    base = """
        You are an Amazons game player. Amazon is a board game with board size 8x8. [游戏规则介绍]
        White pieces are shown as W, and black pieces are shown as B on the board.
        General strategy of the game is: prefer moves that restrict opponent mobility, prefer moves that control central squares, and avoid moves that block your own pieces.
        Now is your turn, to your best ability, please briefly give a overview of the situation, evaluate a few promising moves, provide reason for your final choice, and output the action with specified format.
        Your response format should be:
        Situation: [Your Observation]
        Evaluation: [Your Evaluation]
        Reason: [Your Reason]
        Answer: [Your Answer]
        Output valid action if possible, the coordinate should be in the form of (A,1) -> (B,2) -> (C,3) or (A,1)->(B,2)->(C,3), and this form should appear, and only appear when you give your final answer after "Answer".
        If there is no valid action, output 'None'.
        You MUST select exactly ONE move from the legal move list.
        Output ONLY the move. The output format is: (x0,y0)->(x1,y1)->(x2,y2)
    """
    return base


def build_user_prompt(board_text, moves_text, color):
    if color == -1:
        color_text = "White"
    if color == 1:
        color_text = "Black"
    text = (
        f"Your color is {color_text}\n"
        "Current board information is:\n"
        f"{board_text}\n"
        "Your legal moves are:\n"
        f"{moves_text}"
    )
    return text


def parse_move(text, legal_set):
    if not text:
        return None
    # 全局搜索三段坐标
    m = re.search(
        r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*->\s*"
        r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*->\s*"
        r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)",
        text,
    )
    if not m:
        return None

    move = tuple(int(x) for x in m.groups())
    return move if move in legal_set else None


def normalize_prompt(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\n", " ").replace("\r", " ")).strip()


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
        print(
            json.dumps(
                {
                    "response": {
                        "x0": -1,
                        "y0": -1,
                        "x1": -1,
                        "y1": -1,
                        "x2": -1,
                        "y2": -1,
                    }
                }
            )
        )
        trial_count = 3
    init_board()

    data = json.loads(sys.stdin.readline())
    reqs = data["requests"]
    res = data["responses"]
    turnID = len(res)

    currBotColor = GRID_BLACK if reqs[0]["x0"] < 0 else GRID_WHITE

    beginPos, movePos, arrowPos = find_all_moves(currBotColor)
    posCount = len(beginPos)

    if posCount == 0:
        x0 = y0 = x1 = y1 = x2 = y2 = -1
        print(
            json.dumps(
                {
                    "response": {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    },
                }
            )
        )

    else:
        board_text = board_to_ascii()
        moves_text = moves_to_text(beginPos, movePos, arrowPos)

        legal_set = set(
            (
                beginPos[i][0],
                beginPos[i][1],
                movePos[i][0],
                movePos[i][1],
                arrowPos[i][0],
                arrowPos[i][1],
            )
            for i in range(posCount)
        )

        chosen = None
        for _ in range(3):
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(board_text, moves_text, currBotColor)

            responsed_text, reasoning_text = query_api(
                api_base,
                api_key,
                model_name,
                system_prompt,
                user_prompt,
            )
            parsed = parse_move(responsed_text, legal_set)
            if parsed:
                chosen = parsed
                break

        if chosen is None:
            x0 = y0 = x1 = y1 = x2 = y2 = -1
        else:
            x0, y0, x1, y1, x2, y2 = chosen

        print(
            json.dumps(
                {
                    "response": {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    },
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
